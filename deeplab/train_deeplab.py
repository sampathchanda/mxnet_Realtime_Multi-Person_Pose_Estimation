'''
@author: kohill

'''

from tensorboardX import SummaryWriter
from data_iter import getDataLoader
from resnet_v1_101_deeplab import get_symbol
import mxnet as mx
import logging
BATCH_SIZE = 8
NUM_LINKS = 19
NUM_PARTS =  19
SAVE_PREFIX = "models/resnet-101"
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

def train(retrain = True,start_epoch = 0,ndata = 16,gpus = [0,1]):
    input_shape = (368,368)
    stride = (8,8)
    sym = get_symbol(is_train = True, numberofparts = NUM_PARTS, numberoflinks= NUM_LINKS)
    model = mx.mod.Module(symbol=sym, context=[mx.gpu(g) for g in gpus],label_names  = ["label"])
    model.bind(data_shapes=[('data', (BATCH_SIZE, 3,input_shape[0],input_shape[1]))],
               label_shapes = [("label",(BATCH_SIZE,NUM_PARTS * 2 + (NUM_LINKS * 4) ,
                                        input_shape[0]//stride[0],input_shape[1]//stride[1])),
                               ]
               )        
    summary_writer = SummaryWriter(LOGGING_DIR)
    if retrain:
        args,auxes = load_checkpoint(PRETRAINED_PREFIX,0)
    else:
        args,auxes = load_checkpoint(SAVE_PREFIX,start_epoch)
        
    model.init_params(arg_params=args, aux_params=auxes, allow_missing=retrain,allow_extra = True)
    model.init_optimizer(optimizer='rmsprop', 
                        optimizer_params=(('learning_rate', 0.001 ), ))   
    data_iter = getDataLoader(batch_size = BATCH_SIZE)
    for n_data_wheel in range(ndata):
        model.save_checkpoint(SAVE_PREFIX + "final", n_data_wheel)        
        for nbatch,data_batch in enumerate( data_iter):
            data = mx.nd.array(data_batch[0])
            label = mx.nd.array(data_batch[1])
            model.forward(mx.io.DataBatch(data = [data],label = [label]), is_train=True) 
            prediction=model.get_outputs()
            heatmap_loss = prediction[0].asnumpy()[0]/BATCH_SIZE
            paf_loss = prediction[1].asnumpy()[0] / BATCH_SIZE            
            summary_writer.add_scalar("heatmap_loss", heatmap_loss)
            summary_writer.add_scalar("paf_loss", paf_loss) 
            logging.info("{0} {1} {2} {3}".format(
                n_data_wheel,nbatch, heatmap_loss,paf_loss))
            model.backward()  
            model.update()        
            if nbatch % 100 == 0:
                model.save_checkpoint(SAVE_PREFIX , nbatch )
    
if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO)
    train(retrain = False, start_epoch= 100 , gpus = [0,1])