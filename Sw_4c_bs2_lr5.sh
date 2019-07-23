export PYTHONPATH=$PWD
#export CUDA_LAUNCH_BLOCKING=1 
export CUDA_VISIBLE_DEVICES=1

TEST='--skip-test'
#TEST='--only-test' 

CONFIG_FILE='ROI2D_Sw4c_fpn432_bs2_lr5.yaml'

ipython tools/train_net_sparse3d.py -- --config-file "configs/$CONFIG_FILE"  $TEST

