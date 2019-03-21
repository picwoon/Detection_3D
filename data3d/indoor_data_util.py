# xyz Nov 2018
import open3d
import numpy as np
import os, pathlib, glob, sys
sys.path.insert(0, '..')
from utils3d.bbox3d_ops import Bbox3D
from collections import defaultdict
import pickle
import torch
from utils3d.geometric_util import cam2world_box, cam2world_pcl

#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#ROOT_DIR = os.path.dirname(BASE_DIR)
#sys.path.append(ROOT_DIR)
from wall_preprocessing import show_walls_1by1, show_walls_offsetz

DEBUG = True
if DEBUG:
  from second.data.data_render import DataRender

DSET_DIR = '/DS/SUNCG/suncg_v1'
PARSED_DIR = f'{DSET_DIR}/parsed'
SPLITED_DIR = '/DS/SUNCG/suncg_v1_splited_torch'
MAX_FLOAT_DRIFT = 1e-6
DATASET = 'SUNCG'

def points2pcd_open3d(points):
  assert points.shape[-1] == 3
  pcd = open3d.PointCloud()
  points = points.reshape([-1,3])
  pcd.points = open3d.Vector3dVector(points[:,0:3])
  if points.shape[1] == 6:
    pcd.normals = open3d.Vector3dVector(points[:,3:6])
  return pcd

def points_ply(points, plyfn):
  pcd = points2pcd_open3d(points)
  open3d.write_point_cloud(plyfn, pcd)

def random_sample_pcl(points0, num_points1, only_reduce=False):
  n0 = points0.shape[0]
  if num_points1 == n0:
    return points0
  if num_points1 < n0:
    indices = np.random.choice(n0, num_points1, replace=False)
  else:
    if only_reduce:
      return points0
    indices0 = np.random.choice(n0, num_points1-n0, replace=True)
    indices = np.concatenate([np.arange(n0), indices0])
  points1 = np.take(points0, indices, 0)
  return points1

def add_norm(pcd):
  open3d.estimate_normals(pcd, search_param = open3d.KDTreeSearchParamHybrid(
            radius = 0.1, max_nn = 50))
  return pcd

#def read_summary(base_dir):
#  summary_fn = os.path.join(base_dir, 'summary.txt')
#  summary = {}
#  if not os.path.exists(summary_fn):
#    return summary, False
#  with open(summary_fn, 'r') as f:
#    for line in f:
#      line = line.strip()
#      items = [e for e in line.split(' ') if e!='']
#      summary[items[0][:-1]] = int(items[1])
#  return summary

#def write_summary(base_dir, name, value, style='w'):
#  summary_fn = os.path.join(base_dir, 'summary.txt')
#  with open(summary_fn, style) as f:
#    f.write(f"{name}: {value}\n")
#  print(f'write summary: {summary_fn}')

class IndoorData():
  _block_size0 = np.array([8,8,-1])
  #_block_size0 = np.array([16,16,3])
  _block_stride_rate = np.array([0.8,0.8,0.8])
  _min_pn_inblock = 1000
  _num_points = 100 * 1000

  @staticmethod
  def split_scene(scene_dir, splited_path):
    from suncg import check_house_intact, read_summary, write_summary
    scene_name = os.path.basename(scene_dir)
    splited_path = os.path.join(splited_path, scene_name)
    summary_0 = read_summary(splited_path)
    if 'split_num' in summary_0:
      print(f'skip {splited_path}')
      return
    print(f'spliting {scene_dir}')
    gen_ply = True and DEBUG

    #house_intact, intacts = check_house_intact(scene_dir)
    #if not house_intact:
    #  return
    summary = read_summary(scene_dir)
    if 'level_num' in summary and  summary['level_num'] != 1:
      return

    pcl_fn = os.path.join(scene_dir, 'pcl_camref.ply')
    if not os.path.exists(pcl_fn):
      print(f'pcl.ply not exist, skip {scene_dir}')
      return
    points_splited = IndoorData.split_pcl_plyf(pcl_fn)
    bboxes_splited = {}
    #for obj in ['wall', 'window', 'door']:
    for obj in ['wall']:
      bbox_fn = os.path.join(scene_dir, f'object_bbox/{obj}.txt')
      if os.path.exists(bbox_fn):
        bboxes_splited[obj] = IndoorData.split_bbox(bbox_fn, points_splited)

    n_block = len(points_splited)
    if not os.path.exists(splited_path):
      os.makedirs(splited_path)

    for i in range(n_block):
      fni = splited_path + '/pcl_%d.pth'%(i)
      pcl_i = points_splited[i].astype(np.float32)

      #offset = pcl_i[:,0:3].mean(0)
      #pcl_i[:,0:3] = pcl_i[:,0:3] - offset
      pcl_i = np.ascontiguousarray(pcl_i)

      boxes_i = {}
      for obj in bboxes_splited:
        boxes_i[obj] = bboxes_splited[obj][i].astype(np.float32)
      torch.save((pcl_i, boxes_i), fni)

      if gen_ply:
        Bbox3D.draw_points_bboxes(pcl_i, boxes_i['wall'], 'Z', False)
        pclfn_i = splited_path + f'/pcl_{i}.ply'
        points_ply(pcl_i[:,0:3], pclfn_i)
        boxfn_i = splited_path + f'/wall_{i}.ply'
        Bbox3D.save_bboxes_ply(boxfn_i, boxes_i['wall'], 'Z')
      print(f'save {fni}')
    write_summary(splited_path, 'split_num', n_block, 'w')

  @staticmethod
  def adjust_box_for_thickness_crop(bboxes0):
    # thickness_drift for cropping y
    thickness_drift = 0.02
    size_x_drift = -0.03
    box_offset = np.array([[0,0,0,size_x_drift, thickness_drift, 0,0]])
    bboxes1 = bboxes0 + box_offset
    tmp = np.minimum(0.1, bboxes0[:,3])
    bboxes1[:,3] = np.maximum(bboxes1[:,3], tmp)
    return bboxes1

  @staticmethod
  def split_bbox(bbox_fn, points_splited):
    '''
    bbox in file bbox_fn: up_axis='Y' with always x_size > z_size

    transform with cam2world_box:
      up_axis == 'Z'
      always: x_size > y_size
    '''
    min_point_num_per1sm = 10
    # thickness_aug for cropping x
    thickness_aug = 0.1
    assert IndoorData._block_size0[-1] == -1 # do  not crop box along z

    bboxes = np.loadtxt(bbox_fn).reshape([-1,7])
    #if DEBUG:
    #  #show_walls_1by1(bboxes)
    #  bboxes = bboxes[3:4]

    areas = bboxes[:,3] * bboxes[:,5]
    min_point_num = np.minimum( min_point_num_per1sm * areas, 200 )
    bboxes_aug = bboxes.copy()
    bboxes_aug[:,4] += thickness_aug
    bn = bboxes.shape[0]

    sn = len(points_splited)
    bboxes_splited = []
    for i in range(0, sn):
      #  Use to constrain size_x size_z
      point_masks_aug_i = Bbox3D.points_in_bbox(points_splited[i][:,0:3].copy(), bboxes_aug.copy())
      #  Use to constrain size_y (the thickness)
      bboxes_tc = IndoorData.adjust_box_for_thickness_crop(bboxes)
      point_masks_i = Bbox3D.points_in_bbox(points_splited[i][:,0:3].copy(), bboxes_tc)

      pn_in_box_aug_i = np.sum(point_masks_aug_i, 0)
      pn_in_box_i = np.sum(point_masks_i, 0)
      #print(f'no aug:{pn_in_box_i}\n auged:{pn_in_box_aug_i}')

      # (1) The bboxes with no points with thickness_aug will be removed firstly
      keep_box_aug_i = pn_in_box_aug_i > min_point_num
      bboxes_i = bboxes[keep_box_aug_i]

      points_aug_i = [points_splited[i][point_masks_aug_i[:,j]] for j in range(bn)]
      points_aug_i = [points_aug_i[j] for j in range(bn) if keep_box_aug_i[j]]

      points_i = [points_splited[i][point_masks_i[:,j]] for j in range(bn)]
      points_i = [points_i[j] for j in range(bn) if keep_box_aug_i[j]]

      # (2) Crop all the boxes by points and intersec_corners seperately
      bn_i = bboxes_i.shape[0]
      croped_bboxes_i = []
      keep_unseen_intersection = False
      if keep_unseen_intersection:
        intersec_corners_idx_i, intersec_corners_i = Bbox3D.detect_all_intersection_corners(bboxes_i, 'Z')
      else:
        intersec_corners_idx_i = [None]*bn_i
      for k in range(bn_i):
        croped_bboxes_i.append( Bbox3D.crop_bbox_by_points(
                        bboxes_i[k], points_i[k], points_aug_i[k], 'Z', intersec_corners_idx_i[k]) )
      if len(croped_bboxes_i) > 0:
        croped_bboxes_i = np.concatenate(croped_bboxes_i, 0).reshape([-1,7])
      else:
        croped_bboxes_i = np.array([]).reshape([-1,7])

      # (3) Refine x size of each bbox by thickness croped of intersected bbox
      #croped_size = bboxes_i[:,3:6] - croped_bboxes_i[:,3:6]
      refine_x_by_intersection = False # not correct yet
      if refine_x_by_intersection:
        for k in range(bn_i):
          itsc0, itsc1 = intersec_corners_idx_i[k]
          crop_value = [0,0]
          if itsc0 >= 0:
            crop_value[0] = Bbox3D.refine_intersection_x(croped_bboxes_i[k], 'neg', croped_bboxes_i[itsc0], 'Z')
          if itsc1 >= 0:
            crop_value[1] = Bbox3D.refine_intersection_x(croped_bboxes_i[k], 'pos', croped_bboxes_i[itsc1], 'Z')
          if itsc0 >= 0 or itsc1 > 0:
            croped_bboxes_i[k] = Bbox3D.crop_bbox_size(croped_bboxes_i[k], 'X', crop_value)

          #crop_ysize_neg = croped_size[itsc0,1] if itsc0 >= 0 else 0
          #crop_ysize_pos = croped_size[itsc1,1] if itsc1 >= 0 else 0
          #croped_bboxes_i[k] = Bbox3D.crop_bbox_size(croped_bboxes_i[k], 'X', [crop_ysize_neg, crop_ysize_pos])

      # (4) remove too small wall
      min_wall_size_x = 0.2
      sizex_mask = croped_bboxes_i[:,3] > min_wall_size_x
      croped_bboxes_i = croped_bboxes_i[sizex_mask]
      bboxes_splited.append(croped_bboxes_i)

      show = False
      if show and DEBUG and len(points_i) > 0:
        print(croped_bboxes_i[:,3])
        points = np.concatenate(points_i,0)
        points = points_splited[i]
        points1 = points.copy()
        points1[:,0] += 12
        points = np.concatenate([points, points1], 0)
        bboxes_i[:,0] += 12
        bboxes_i = np.concatenate([bboxes_i, croped_bboxes_i], 0)
        Bbox3D.draw_points_bboxes(points, bboxes_i, up_axis='Z', is_yx_zb=False)
        import pdb; pdb.set_trace()  # XXX BREAKPOINT
        pass
    return bboxes_splited

  @staticmethod
  def split_pcl_plyf(pcl_fn):
    assert os.path.exists(pcl_fn)
    pcd = open3d.read_point_cloud(pcl_fn)
    points = np.asarray(pcd.points)
    points = cam2world_pcl(points)
    pcd.points = open3d.Vector3dVector(points)
    is_add_norm = True
    if is_add_norm:
      add_norm(pcd)
      normals = np.asarray(pcd.normals)
      points = np.concatenate([points, normals], -1)
    #open3d.draw_geometries([pcd])
    points_splited = IndoorData.points_splited(points)
    return points_splited

  @staticmethod
  def points_splited(points):
    splited_vidx, block_size = IndoorData.split_xyz(points[:,0:3],
            IndoorData._block_size0.copy(), IndoorData._block_stride_rate,
            IndoorData._min_pn_inblock)
    if splited_vidx[0] is None:
      points_splited = [points]
    else:
      points_splited = [np.take(points, vidx, axis=0) for vidx in splited_vidx]

    pnums0 = [p.shape[0] for p in points_splited]
    #print(pnums0)
    points_splited = [random_sample_pcl(p, IndoorData._num_points, only_reduce=True)
                        for p in points_splited]

    show = False
    if show:
      pcds = [points2pcd_open3d(points) for points in points_splited]
      #open3d.draw_geometries(pcds)
      for pcd in pcds:
        open3d.draw_geometries([pcd])

    return points_splited

  @staticmethod
  def autoadjust_block_size(self, xyz_scope, num_vertex0):
    # keep xy area within the threshold, adjust to reduce block num
    _x,_y,_z = self.block_size
    _xy_area = _x*_y
    x0,y0,z0 = xyz_scope
    xy_area0 = x0*y0

    nv_rate = 1.0*num_vertex0/self.num_point

    if xy_area0 <= _xy_area or nv_rate<=1.0:
      #Use one block: (1) small area (2) Very small vertex number
      x2 = x0
      y2 = y0

    else:
      # Need to use more than one block. Try to make block num less which is
      # make x2, y2 large.
      # (3) Large area with large vertex number, use _x, _y
      # (4) Large area with not loo large vertex num. Increase the block size by
      # vertex num rate.
      dis_rate = math.sqrt(nv_rate)
      x1 = x0 / dis_rate * 0.9
      y1 = y0 / dis_rate * 0.9
      x2 = max(_x, x1)
      y2 = max(_y, y1)

    block_size= np.array([x2, y2, _z])
    block_size = np.ceil(10*block_size)/10.0
    print('xyz_scope:{}\nblock_size:{}'.format(xyz_scope, block_size))
    return block_size

  @staticmethod
  def split_xyz(xyz, block_size0, block_stride_rate, min_pn_inblock, dynamic_block_size=False):
    xyz_min = np.min(xyz, 0)
    xyz_max = np.max(xyz, 0)
    xyz_scope = xyz_max - xyz_min
    num_vertex0 = xyz.shape[0]

    if dynamic_block_size:
      block_size = autoadjust_block_size(xyz_scope, num_vertex0)
    else:
      block_size = block_size0
    if block_size[2] == -1:
      block_size[2] = np.ceil(xyz_scope[-1])
    block_stride = block_stride_rate * block_size
    block_dims0 =  (xyz_scope - block_size) / block_stride + 1
    block_dims0 = np.maximum(block_dims0, 1)
    block_dims = np.ceil(block_dims0).astype(np.int32)
    #print(block_dims)
    xyzindices = [np.arange(0, k) for k in block_dims]
    bot_indices = [np.array([[xyzindices[0][i], xyzindices[1][j], xyzindices[2][k]]]) for i in range(block_dims[0]) \
                   for j  in range(block_dims[1]) for k in range(block_dims[2])]
    bot_indices = np.concatenate(bot_indices, 0)
    bot = bot_indices * block_stride
    top = bot + block_size

    block_num = bot.shape[0]
    #print('raw scope:\n{} \nblock_num:{}'.format(xyz_scope, block_num))
    #print('splited bot:\n{} splited top:\n{}'.format(bot, top))

    if block_num == 1:
      return [None], block_size

    if block_num>1:
      for i in range(block_num):
        for j in range(3):
          if top[i,j] > xyz_scope[j]:
            top[i,j] = xyz_scope[j] - MAX_FLOAT_DRIFT
            bot[i,j] = np.maximum(xyz_scope[j] - block_size[j] + MAX_FLOAT_DRIFT, 0)

    bot += xyz_min
    top += xyz_min

    dls_splited = []
    num_points_splited = []
    splited_vidx = []
    for i in range(block_num):
      mask0 = xyz >= bot[i]
      mask1 = xyz < top[i]
      mask = mask0 * mask1
      mask = np.all(mask, 1)
      new_n = np.sum(mask)
      indices = np.where(mask)[0]
      num_point_i = indices.size
      if num_point_i < min_pn_inblock:
        #print('num point {} < {}, block {}/{}'.format(num_point_i,\
        #                                self.num_point * 0.1, i, block_num))
        continue
      num_points_splited.append(num_point_i)
      splited_vidx.append(indices)

    num_vertex_splited = [d.shape[0] for d in splited_vidx]
    return splited_vidx, block_size


def read_house_names(fn):
  with open(fn) as f:
    lines = f.readlines()
  lines = [line.strip() for line in lines]
  return lines

def box3d_t_2d(box3d, P2):
  from second.core.box_np_ops import center_to_corner_box3d, project_to_image
  locs = box3d[:, :3]
  dims = box3d[:, 3:6]
  angles = box3d[:,6]
  camera_box_origin = [0.5,1.0,0.5]
  box_corners_3d =  center_to_corner_box3d(
                    locs, dims, angles, camera_box_origin, axis=1)
  box_corners_in_image = project_to_image(box_corners_3d, P2)

  minxy = np.min(box_corners_in_image, axis=1)
  maxxy = np.max(box_corners_in_image, axis=1)
  box_2d_preds = np.concatenate([minxy, maxxy], axis=1)
  return box_2d_preds

def get_box3d_cam(box3d_lidar, rect, Trv2c):
  from second.core.box_np_ops import box_lidar_to_camera
  box3d_cam = box_lidar_to_camera(box3d_lidar, rect, Trv2c)
  return box3d_cam

def get_alpha(box3d_lidar):
  return -np.arctan2(-box3d_lidar[:,1], box3d_lidar[:,0]) + box3d_lidar[:,6]

def get_sung_info(data_path, house_names0):
  data_path = os.path.join(data_path, 'houses')
  house_names1 = os.listdir(data_path)
  house_names = [h for h in house_names1 if h in house_names0]

  infos = []
  for house in house_names:
    house_path = os.path.join(data_path, house)
    object_path = os.path.join(house_path, 'objects')

    pcl_fns = glob.glob(os.path.join(house_path, 'pcl*.bin'))
    pcl_fns.sort()
    #pcl_fns = [pcl_fn.split('houses')[1] for pcl_fn in pcl_fns]
    pcl_num = len(pcl_fns)

    box_fns = glob.glob(os.path.join(object_path, '*.bin'))
    box_fns.sort()
    objects = set([os.path.basename(fn).split('_')[0] for fn in box_fns])

    for i in range(pcl_num):
      info = {}
      info['velodyne_path'] = pcl_fns[i]
      info['pointcloud_num_features'] = 6

      info['image_idx'] = '0'
      info['image_path'] = 'empty'
      info['calib/R0_rect'] = np.eye(4)
      info['calib/Tr_velo_to_cam'] = np.eye(4) # np.array([[0,-1,0,0]. [0,0,-1,0], [1,0,0,0], [0,0,0,1]], dtype=np.float32)
      info['calib/P2'] = np.eye(4)

      base_name = os.path.splitext( os.path.basename(pcl_fns[i]) )[0]
      idx = int(base_name.split('_')[-1])

      annos = defaultdict(list)
      for obj in objects:
        box_fn = os.path.join(object_path, obj+'_'+str(idx)+'.bin')
        box = np.fromfile(box_fn, np.float32)
        box = box.reshape([-1,7])
        box = Bbox3D.convert_to_yx_zb_boxes(box)
        box_num = box.shape[0]
        annos['location'].append(box[:,0:3])
        annos['dimensions'].append(box[:,3:6])
        annos['rotation_y'].append(box[:,6])
        annos['name'].append( np.array([obj]*box_num) )

        annos['difficulty'].append(np.array(['A']*box_num))
        annos['bbox'].append( box3d_t_2d(box, info['calib/P2'] ) )
        annos['box3d_camera'].append( get_box3d_cam(box, info['calib/R0_rect'], info['calib/Tr_velo_to_cam']) )
        bn = box.shape[0]
        annos["truncated"].append(np.array([0.0]*bn))
        annos["occluded"].append(np.array([0.0]*bn))
        annos["alpha"].append( get_alpha(box) )

      for key in annos:
        annos[key] = np.concatenate(annos[key], 0)

      info['annos'] = annos

      infos.append(info)
  return infos

def creat_indoor_info_file(data_path=SPLITED_DIR,
                           save_path=None,
                           create_trainval=False,
                           relative_path=True):
    '''
    Load splited bbox in standard type and bin format.
    Save in picke format and bbox of yx_zb type.
    '''
    house_names = {}
    house_names['train'] = read_house_names("%s/train_test_splited/train.txt"%(data_path))
    house_names['val'] = read_house_names("%s/train_test_splited/val.txt"%(data_path))

    #house_names['train'] = ['001188c384dd72ce2c2577d034b5cc92']
    #house_names['val'] = ['001188c384dd72ce2c2577d034b5cc92']

    print("Generate info. this may take several minutes.")
    if save_path is None:
        save_path = pathlib.Path(data_path)
    else:
        save_path = pathlib.Path(save_path)

    for split in house_names:
      sung_infos = get_sung_info(data_path, house_names[split])
      filename = save_path / pathlib.Path('sung_infos_%s.pkl'%(split))
      print(f"sung info {split} file is saved to {filename}")
      import pdb; pdb.set_trace()  # XXX BREAKPOINT
      with open(filename, 'wb') as f:
          pickle.dump(sung_infos, f)

def read_indoor_info():
  info_path = f'{SPLITED_DIR}/sung_infos_train.pkl'
  with open(info_path, 'rb') as f:
    infos = pickle.load(f)
  idx = 0
  print(f'totally {len(infos)} blocks')
  for idx in range(0,len(infos)):
    info = infos[idx]
    pcl_path = info['velodyne_path']
    pointcloud_num_features = info['pointcloud_num_features']
    points = np.fromfile( pcl_path, dtype=np.float32).reshape([-1, pointcloud_num_features])

    annos = info['annos']
    loc = annos['location']
    dims = annos['dimensions']
    rots = annos['rotation_y']
    gt_boxes = np.concatenate([loc, dims, rots[..., np.newaxis]], axis=1).astype(np.float32)

    Bbox3D.draw_points_bboxes(points, gt_boxes, 'Z', is_yx_zb=True)

def get_house_names_1level():
  house_names_1level_fn = f'{DSET_DIR}/house_names_1level.txt'
  with open(house_names_1level_fn, 'r') as f:
    house_names_1level = [l.strip() for l in f.readlines()]
  return house_names_1level


def creat_splited_pcl_box():
  '''
  Load parsed objects for whole scene. Split house, generate splited point cloud,and bbox.
  Splited point cloud saved in bin.
  Splited bbox saved in bin with standard type.
  '''
  parsed_dir = PARSED_DIR
  splited_path = f'{SPLITED_DIR}/houses'
  house_names = os.listdir(parsed_dir)
  house_names.sort()

  #house_names = ['28297783bce682aac7fb35a1f35f68fa'] # yaw!=0
  #house_names = ['001188c384dd72ce2c2577d034b5cc92']  # a lot of unseen corners
  #house_names = ['001188c384dd72ce2c2577d034b5cc92']
  house_names = ['31a69e882e51c7c5dfdc0da464c3c02d']
  house_names = ['7411df25770eaf8d656cac2be42a9af0']
  house_names = ['8c033357d15373f4079b1cecef0e065a']
  #house_names = get_house_names_1level()

  scene_dirs = [os.path.join(parsed_dir, s) for s in house_names]
  scene_dirs.sort()
  for scene_dir in scene_dirs:
    IndoorData.split_scene(scene_dir, splited_path)
    print(f'split ok: {scene_dir}')

def gen_train_list():
  house_names = os.listdir(os.path.join(SPLITED_DIR, 'houses'))
  num = len(house_names)
  train_num = int(num*0.8)
  train_hosue_names = house_names[0:train_num]
  test_house_names = house_names[train_num:]

  split_path = os.path.join(SPLITED_DIR, 'train_test_splited')
  if not os.path.exists(split_path):
    os.makedirs(split_path)
  train_fn = os.path.join(split_path, 'train.txt')
  test_fn = os.path.join(split_path, 'val.txt')
  with open(train_fn, 'w') as f:
    f.write('\n'.join(train_hosue_names))
  with open(test_fn, 'w') as f:
    f.write('\n'.join(test_house_names))


if __name__ == '__main__':
  creat_splited_pcl_box()
  #creat_indoor_info_file()
  #read_indoor_info()
  #gen_train_list()
  pass
