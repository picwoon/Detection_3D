// Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#include <ATen/ATen.h>
#include <ATen/cuda/CUDAContext.h>

#include <THC/THC.h>
#include <THC/THCAtomics.cuh>
#include <THC/THCDeviceUtils.cuh>

// TODO make it in a common file
#define CUDA_1D_KERNEL_LOOP(i, n)                            \
  for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < n; \
       i += blockDim.x * gridDim.x)


template <typename T>
__device__ T bilinear_interpolate(
        const T* bottom_data,
        const int height, 
        const int width,
        const int zsize,
        T y, 
        T x,
        T z,
        const int index /* index for debug only*/) {

  // deal with cases that inverse elements are out of feature map boundary
  if (y < -1.0 || y > height || x < -1.0 || x > width || z < -1.0 || zsize> zsize) {
    //empty
    return 0;
  }

  if (y <= 0) y = 0;
  if (x <= 0) x = 0;
  if (z <= 0) z = 0;

  int y_low = (int) y;
  int x_low = (int) x;
  int z_low = (int) z;
  int y_high;
  int x_high;
  int z_high;

  if (y_low >= height - 1) {
    y_high = y_low = height - 1;
    y = (T) y_low;
  } else {
    y_high = y_low + 1;
  }

  if (x_low >= width - 1) {
    x_high = x_low = width - 1;
    x = (T) x_low;
  } else {
    x_high = x_low + 1;
  }

  if (z_low >= zsize - 1) {
    z_high = z_low = zsize - 1;
    z = (T) z_low;
  } else {
    z_high = z_low + 1;
  }

  T ly = y - y_low;
  T lx = x - x_low;
  T lz = z - z_low;
  T hy = 1. - ly, hx = 1. - lx, hz = 1. - lz;
  // do bilinear interpolation
  T v1 = bottom_data[y_low  * width * zsize + x_low  * zsize + z_low];
  T v2 = bottom_data[y_low  * width * zsize + x_high * zsize + z_low];
  T v3 = bottom_data[y_high * width * zsize + x_low  * zsize + z_low];
  T v4 = bottom_data[y_high * width * zsize + x_high * zsize + z_low];

  T v5 = bottom_data[y_low  * width * zsize + x_low  * zsize + z_high];
  T v6 = bottom_data[y_low  * width * zsize + x_high * zsize + z_high];
  T v7 = bottom_data[y_high * width * zsize + x_low  * zsize + z_high];
  T v8 = bottom_data[y_high * width * zsize + x_high * zsize + z_high];

  T w1 = hy * hx * hz, w2 = hy * lx * hz, w3 = ly * hx * hz, w4 = ly * lx * hz;
  T w5 = hy * hx * lz, w6 = hy * lx * lz, w7 = ly * hx * lz, w8 = ly * lx * lz;

  T val = (w1 * v1 + w2 * v2 + w3 * v3 + w4 * v4   +   w5 * v5 + w6 * v6 + w7 * v7 + w8 * v8);

  return val;
}

//**********************************************************************************************

template <typename T>
__global__ void RoIAlignRotatedForward(
    const int nthreads,
    const T* bottom_data,
    const T spatial_scale,
    const int channels,
    const int height,
    const int width,
    const int zsize,
    const int pooled_height,
    const int pooled_width,
    const int pooled_zsize,
    const int sampling_ratio,
    const T* bottom_rois,
    T* top_data) {
  CUDA_1D_KERNEL_LOOP(index, nthreads) {
    // (n, c, ph, pw, pz) is an element in the pooled output
    int pz = index % pooled_zsize
    int pw = (index / pooled_zsize) % pooled_width;
    int ph = (index  / pooled_zsize/ pooled_width) % pooled_height;
    int c = (index  / pooled_zsize/ pooled_width / pooled_height) % channels;
    int n = index  / pooled_zsize/ pooled_width / pooled_height / channels;

    const T* offset_bottom_rois = bottom_rois + n * 8;
    int roi_batch_ind = offset_bottom_rois[0];

    // Do not round
    T roi_center_w = offset_bottom_rois[1] * spatial_scale;
    T roi_center_h = offset_bottom_rois[2] * spatial_scale;
    T roi_center_z = offset_bottom_rois[3] * spatial_scale;
    T roi_width = offset_bottom_rois[4] * spatial_scale;
    T roi_height = offset_bottom_rois[5] * spatial_scale;
    T roi_zsize = offset_bottom_rois[6] * spatial_scale;
    T theta = offset_bottom_rois[7] * M_PI / 180.0;

    // Force malformed ROIs to be 1x1
    roi_width = max(roi_width, (T)1.);
    roi_height = max(roi_height, (T)1.);
    roi_zsize = max(roi_zsize, (T)1.);
    T bin_size_h = static_cast<T>(roi_height) / static_cast<T>(pooled_height);
    T bin_size_w = static_cast<T>(roi_width) / static_cast<T>(pooled_width);
    T bin_size_z = static_cast<T>(roi_zsize) / static_cast<T>(pooled_zsize);

    const T* offset_bottom_data =
        bottom_data + (roi_batch_ind * channels + c) * height * width * zsize;

    // We use roi_bin_grid to sample the grid and mimic integral
    int roi_bin_grid_h = 
        (sampling_ratio > 0) ? sampling_ratio : ceil(roi_height / pooled_height); // e.g., = 2
    int roi_bin_grid_w =
        (sampling_ratio > 0) ? sampling_ratio : ceil(roi_width / pooled_width);
    int roi_bin_grid_z =
        (sampling_ratio > 0) ? sampling_ratio : ceil(roi_zsize / pooled_zsize);

    // roi_start_h and roi_start_w are computed wrt the center of RoI (x, y).
    // Appropriate translation needs to be applied after.
    T roi_start_h = -roi_height / 2.0;
    T roi_start_w = -roi_width / 2.0;
    T roi_start_z = -roi_zsize / 2.0;
    T cosTheta = cos(theta);
    T sinTheta = sin(theta);

    // We do average (integral) pooling inside a bin
    const T count = roi_bin_grid_h * roi_bin_grid_w * roi_bin_grid_z; // e.g. = 4

    T output_val = 0.;
    for (int iy = 0; iy < roi_bin_grid_h; iy++) // e.g., iy = 0, 1
    {
      const T yy = roi_start_h + ph * bin_size_h + static_cast<T>(iy + .5f) * bin_size_h / static_cast<T>(roi_bin_grid_h); // e.g., 0.5, 1.5
      for (int ix = 0; ix < roi_bin_grid_w; ix++) {
        const T xx = roi_start_w + pw * bin_size_w + static_cast<T>(ix + .5f) * bin_size_w / static_cast<T>(roi_bin_grid_w);
        for (int iz = 0; iz < roi_bin_grid_z; iz++) {
          const T zz = roi_start_z + pz * bin_size_z + static_cast<T>(iz + .5f) * bin_size_z / static_cast<T>(roi_bin_grid_z);

          // Rotate by theta around the center and translate
          T x = xx * cosTheta + yy * sinTheta + roi_center_w;
          T y = yy * cosTheta - xx * sinTheta + roi_center_h;
          T z = z + roi_center_z

          T val = bilinear_interpolate(
              offset_bottom_data, height, width, zsize y, x, z, index);
          output_val += val;
      }
    }
    output_val /= count;

    top_data[index] = output_val;
  }
}

//**********************************************************************************************

template <typename T>
__device__ void bilinear_interpolate_gradient(
    const int height, const int width, const int zsize,
    T y, T x, T z,
    T & w1, T & w2, T & w3, T & w4, T & w5, T & w6, T & w7, T & w8,
    int & x_low, int & x_high, int & y_low, int & y_high, int & z_low, int & z_high,
    const int index /* index for debug only*/) {

  // deal with cases that inverse elements are out of feature map boundary
  if (y < -1.0 || y > height || x < -1.0 || x > width || z < -1.0 || z > zsize) {
    //empty
    w1 = w2 = w3 = w4 = 0.;
    x_low = x_high = y_low = y_high = z_low = z_high = -1;
    return;
  }

  if (y <= 0) y = 0;
  if (x <= 0) x = 0;
  if (z <= 0) z = 0;

  y_low = (int) y;
  x_low = (int) x;
  z_low = (int) z;

  if (y_low >= height - 1) {
    y_high = y_low = height - 1;
    y = (T) y_low;
  } else {
    y_high = y_low + 1;
  }

  if (x_low >= width - 1) {
    x_high = x_low = width - 1;
    x = (T) x_low;
  } else {
    x_high = x_low + 1;
  }

  if (z_low >= zsize - 1) {
    z_high = z_low = zsize - 1;
    z = (T) z_low;
  } else {
    z_high = z_low + 1;
  }

  T ly = y - y_low;
  T lx = x - x_low;
  T lz = z - z_low;
  T hy = 1. - ly, hx = 1. - lx, hz = 1. - lz;

  w1 = hy * hx * hz, w2 = hy * lx * hz, w3 = ly * hx * hz, w4 = ly * lx * hz;
  w5 = hy * hx * lz, w6 = hy * lx * lz, w7 = ly * hx * lz, w8 = ly * lx * lz;

  return;
}

template <typename T>
__global__ void RoIAlignRotatedBackwardFeature(
    const int nthreads, 
    const T* top_diff,
    const int num_rois, 
    const T spatial_scale,
    const int channels, 
    const int height, 
    const int width,
    const int zsize,
    const int pooled_height, 
    const int pooled_width,
    const int pooled_zsize,
    const int sampling_ratio,
    T* bottom_diff,
    const T* bottom_rois) {
  CUDA_1D_KERNEL_LOOP(index, nthreads) {
    // (n, c, ph, pw, pz) is an element in the pooled output
    int pz = index % pooled_zsize
    int pw = (index / pooled_zsize) % pooled_width;
    int ph = (index  / pooled_zsize/ pooled_width) % pooled_height;
    int c = (index  / pooled_zsize/ pooled_width / pooled_height) % channels;
    int n = index  / pooled_zsize/ pooled_width / pooled_height / channels;

    const T* offset_bottom_rois = bottom_rois + n * 8;
    int roi_batch_ind = offset_bottom_rois[0];

    // Do not using rounding; this implementation detail is critical
    T roi_center_w = offset_bottom_rois[1] * spatial_scale;
    T roi_center_h = offset_bottom_rois[2] * spatial_scale;
    T roi_center_z = offset_bottom_rois[3] * spatial_scale;
    T roi_width = offset_bottom_rois[4] * spatial_scale;
    T roi_height = offset_bottom_rois[5] * spatial_scale;
    T roi_zsize = offset_bottom_rois[6] * spatial_scale;
    T theta = offset_bottom_rois[7] * M_PI / 180.0;
    // T roi_center_w = round(offset_bottom_rois[1] * spatial_scale);
    // T roi_center_h = round(offset_bottom_rois[2] * spatial_scale);
    // T roi_width = round(offset_bottom_rois[3] * spatial_scale);
    // T roi_height = round(offset_bottom_rois[4] * spatial_scale);

    // Force malformed ROIs to be 1x1
    roi_width = max(roi_width, (T)1.);
    roi_height = max(roi_height, (T)1.);
    roi_zsize = max(roi_zsize, (T)1.);
    T bin_size_h = static_cast<T>(roi_height) / static_cast<T>(pooled_height);
    T bin_size_w = static_cast<T>(roi_width) / static_cast<T>(pooled_width);
    T bin_size_z = static_cast<T>(roi_zsize) / static_cast<T>(pooled_zsize);

    T* offset_bottom_diff = bottom_diff + (roi_batch_ind * channels + c) * height * width * zsize;

    int top_offset    = (n * channels + c) * pooled_height * pooled_width * pooled_zsize;
    const T* offset_top_diff = top_diff + top_offset;
    const T top_diff_this_bin = offset_top_diff[ph * pooled_width * pooled_zsize + pw * pooled_zsize + pz];

    // We use roi_bin_grid to sample the grid and mimic integral
    int roi_bin_grid_h = (sampling_ratio > 0) ? sampling_ratio : ceil(roi_height / pooled_height); // e.g., = 2
    int roi_bin_grid_w = (sampling_ratio > 0) ? sampling_ratio : ceil(roi_width / pooled_width);
    int roi_bin_grid_z = (sampling_ratio > 0) ? sampling_ratio : ceil(roi_zsize / pooled_zsize);

    // roi_start_h and roi_start_w are computed wrt the center of RoI (x, y).
    // Appropriate translation needs to be applied after.
    T roi_start_h = -roi_height / 2.0;
    T roi_start_w = -roi_width / 2.0;
    T roi_start_z = -roi_zsize / 2.0;
    T cosTheta = cos(theta);
    T sinTheta = sin(theta);

    // We do average (integral) pooling inside a bin
    const T count = roi_bin_grid_h * roi_bin_grid_w * roi_bin_grid_z; // e.g. = 4

    for (int iy = 0; iy < roi_bin_grid_h; iy ++) // e.g., iy = 0, 1
    {
      const T yy = roi_start_h + ph * bin_size_h + static_cast<T>(iy + .5f) * bin_size_h / static_cast<T>(roi_bin_grid_h); // e.g., 0.5, 1.5
      for (int ix = 0; ix < roi_bin_grid_w; ix ++)
      {
        const T xx = roi_start_w + pw * bin_size_w + static_cast<T>(ix + .5f) * bin_size_w / static_cast<T>(roi_bin_grid_w);

        for (int iz = 0; iz < roi_bin_grid_z; iz ++)
        {
          const T zz = roi_start_z + pz * bin_size_z + static_cast<T>(iz + .5f) * bin_size_z / static_cast<T>(roi_bin_grid_z);
          // Rotate by theta around the center and translate
          T x = xx * cosTheta + yy * sinTheta + roi_center_w;
          T y = yy * cosTheta - xx * sinTheta + roi_center_h;
          T z = zz + roi_center_z;

          T w1, w2, w3, w4, w5, w6, w7, w8;
          int x_low, x_high, y_low, y_high, z_low, z_high;

          bilinear_interpolate_gradient(height, width, zsize, y, x, z,
            w1, w2, w3, w4, w5, w6, w7, w8,
            x_low, x_high, y_low, y_high, z_low, z_high,
            index);

          T g1 = top_diff_this_bin * w1 / count;
          T g2 = top_diff_this_bin * w2 / count;
          T g3 = top_diff_this_bin * w3 / count;
          T g4 = top_diff_this_bin * w4 / count;
          T g5 = top_diff_this_bin * w5 / count;
          T g6 = top_diff_this_bin * w6 / count;
          T g7 = top_diff_this_bin * w7 / count;
          T g8 = top_diff_this_bin * w8 / count;

          if (x_low >= 0 && x_high >= 0 && y_low >= 0 && y_high >= 0 && z_low >= 0 && z_high >= 0)
          {
            atomicAdd(offset_bottom_diff + y_low  * width * zsize + x_low  * zsize + z_low,  static_cast<T>(g1));
            atomicAdd(offset_bottom_diff + y_low  * width * zsize + x_high * zsize + z_low,  static_cast<T>(g2));
            atomicAdd(offset_bottom_diff + y_high * width * zsize + x_low  * zsize + z_low,  static_cast<T>(g3));
            atomicAdd(offset_bottom_diff + y_high * width * zsize + x_high * zsize + z_low,  static_cast<T>(g4));
            atomicAdd(offset_bottom_diff + y_low  * width * zsize + x_low  * zsize + z_high, static_cast<T>(g1));
            atomicAdd(offset_bottom_diff + y_low  * width * zsize + x_high * zsize + z_high, static_cast<T>(g2));
            atomicAdd(offset_bottom_diff + y_high * width * zsize + x_low  * zsize + z_high, static_cast<T>(g3));
            atomicAdd(offset_bottom_diff + y_high * width * zsize + x_high * zsize + z_high, static_cast<T>(g4));
          } // if
      } // ix
    } // iy
  } // CUDA_1D_KERNEL_LOOP
} // RoIAlignBackward


at::Tensor ROIAlignRotated_forward_cuda(const at::Tensor& input,
                                 const at::Tensor& rois,
                                 const float spatial_scale,
                                 const int pooled_height,
                                 const int pooled_width,
                                 const int pooled_zsize,
                                 const int sampling_ratio) {
  AT_ASSERTM(input.type().is_cuda(), "input must be a CUDA tensor");
  AT_ASSERTM(rois.type().is_cuda(), "rois must be a CUDA tensor");

  auto num_rois = rois.size(0);
  auto channels = input.size(1);
  auto height = input.size(2);
  auto width = input.size(3);
  auto zsize = input.size(4);

  auto output = at::empty({num_rois, channels, pooled_height, pooled_width, pooled_zsize}, input.options());
  auto output_size = num_rois * pooled_height * pooled_width * pooled_zsize * channels;
  cudaStream_t stream = at::cuda::getCurrentCUDAStream();

  dim3 grid(std::min(THCCeilDiv((long)output_size, 512L), 4096L));
  dim3 block(512);

  if (output.numel() == 0) {
    THCudaCheck(cudaGetLastError());
    return output;
  }

  AT_DISPATCH_FLOATING_TYPES(input.type(), "ROIAlignRotated_forward", [&] {
    RoIAlignRotatedForward<scalar_t><<<grid, block, 0, stream>>>(
         output_size,
         input.contiguous().data<scalar_t>(),
         spatial_scale,
         channels,
         height,
         width,
         zsize,
         pooled_height,
         pooled_width,
         pooled_zsize,
         sampling_ratio,
         rois.contiguous().data<scalar_t>(),
         output.data<scalar_t>());
  });
  THCudaCheck(cudaGetLastError());
  return output;
}

// TODO remove the dependency on input and use instead its sizes -> save memory
at::Tensor ROIAlignRotated_backward_cuda(const at::Tensor& grad,
                                  const at::Tensor& rois,
                                  const float spatial_scale,
                                  const int pooled_height,
                                  const int pooled_width,
                                  const int pooled_zsize,
                                  const int batch_size,
                                  const int channels,
                                  const int height,
                                  const int width,
                                  const int zsize,
                                  const int sampling_ratio) {
  AT_ASSERTM(grad.type().is_cuda(), "grad must be a CUDA tensor");
  AT_ASSERTM(rois.type().is_cuda(), "rois must be a CUDA tensor");

  auto num_rois = rois.size(0);
  auto grad_input = at::zeros({batch_size, channels, height, width, zsize}, grad.options());

  cudaStream_t stream = at::cuda::getCurrentCUDAStream();

  dim3 grid(std::min(THCCeilDiv((long)grad.numel(), 512L), 4096L));
  dim3 block(512);

  // handle possibly empty gradients
  if (grad.numel() == 0) {
    THCudaCheck(cudaGetLastError());
    return grad_input;
  }

  AT_DISPATCH_FLOATING_TYPES(grad.type(), "ROIAlignRotated_backward", [&] {
    RoIAlignRotatedBackwardFeature<scalar_t><<<grid, block, 0, stream>>>(
         grad.numel(),
         grad.contiguous().data<scalar_t>(),
         num_rois,
         spatial_scale,
         channels,
         height,
         width,
         zsize,
         pooled_height,
         pooled_width,
         pooled_zsize,
         sampling_ratio,
         grad_input.data<scalar_t>(),
         rois.contiguous().data<scalar_t>());
  });
  THCudaCheck(cudaGetLastError());
  return grad_input;
}
