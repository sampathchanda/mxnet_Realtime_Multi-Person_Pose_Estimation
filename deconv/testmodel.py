'''
@author: kohill

'''

from tensorboardX import SummaryWriter
from coco_data_iter import getDataLoader
from resnet_v1_101_deeplab_deconv import get_symbol
import mxnet as mx
import logging,os,cv2
import numpy as np
import matplotlib.pyplot as plt
BATCH_SIZE = 1
NUM_LINKS = 608//2
NUM_PARTS =  288
SAVE_PREFIX = "models/resnet-101final"
EPOCH =25
PRETRAINED_PREFIX = "pre/deeplab_cityscapes"
LOGGING_DIR = "logs"
def load_checkpoint(prefix, epoch):

    save_dict = mx.nd.load('%s-%04d.params' % (prefix, epoch))
    arg_params = {}
    aux_params = {}
    for k, v in save_dict.items():
        tp, name = k.split(':', 1)
        if tp == 'arg':
            arg_params[name] = v
        if tp == 'aux':
            aux_params[name] = v
    return arg_params, aux_params

def test():
    input_shape = (368,368)
    sym = get_symbol(is_train = False, numberofparts = NUM_PARTS, numberoflinks= NUM_LINKS)
    model = mx.mod.Module(symbol=sym, context=[mx.gpu(0)],label_names  = ["label"])
    model.bind(data_shapes=[('data', (1, 3,input_shape[0],input_shape[1]))],
               )        
    args,auxes = load_checkpoint(SAVE_PREFIX,EPOCH)
    model.init_params(arg_params=args, aux_params=auxes, allow_missing=False,allow_extra = True)
    for x,_,z in os.walk("/home/kohill/hszc/data/temp"):
        for name in z:
            img_path = os.path.join(x,name)
            print(img_path)
            ori_img = cv2.imread(img_path)
            fscale = 368.0/ori_img.shape[0]
            img = cv2.resize(ori_img,(0,0),fx = fscale,fy = fscale)
            pads = lambda x: x + 8 - x%8 if x %8 != 0 else x 
            img_padded = np.zeros(shape = (pads(img.shape[0]),pads(img.shape[1]),img.shape[2]),dtype = img.dtype)
            img_padded[:img.shape[0],:img.shape[1],:img.shape[2]] = img
#             img = cv2.resize(ori_img,(368,368))
            
            img = np.transpose(img,(2,0,1))
            model.forward(mx.io.DataBatch(data = [mx.nd.array(img[np.newaxis,:])]), is_train=False), 
            result = model.get_outputs()[0].asnumpy()[0]
            from coco_data_iter import DataIter
            print(result.shape)
#             heatmap  = result
            heatmap = DataIter.im_expand(result)
#             heatmap= cv2.GaussianBlur(heatmap,(5,5),1)
#             heatmap = np.moveaxis(result, 0, -1)
            
            
            print(heatmap.shape,ori_img.shape)
            fig, axes = plt.subplots(1, 3, figsize=(45, 45),
                                 subplot_kw={'xticks': [], 'yticks': []})
            fig.subplots_adjust(hspace=0.3, wspace=0.05)             
            axes[0].imshow(np.max(heatmap,axis = 2))
            axes[1].imshow(ori_img)
            axes[2].imshow(heatmap[:,:,-1])

            plt.show()
if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO)
    test()