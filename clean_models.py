import  glob, os
path = './results_nms1_difyl_lr3'
f = open(f'{path}/last_checkpoint', 'r')
checkpoint = './'+f.readlines()[0]
fnames = glob.glob(f'{path}/model_*.pth')
final = f'{path}/model_final.pth'
for s in fnames:
  if s == checkpoint or s==final:
    continue
  os.remove(s)
  print(f'{s} removed')
print('clean ok')