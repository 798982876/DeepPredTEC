'''
Author: Sneha Singhania
Date: June 3, 2018
Comment: This file contains the main program. The computation graph for ST-ResNet is built and launched in a session.
'''

from st_resnet import Graph
import tensorflow as tf
from params import Params as param
from tqdm import tqdm
from utils import batch_generator
import numpy as np
import h5py

if __name__ == '__main__': 
    #build the computation graph
    g = Graph()
    print ("Computation graph for ST-ResNet loaded\n")
    
    
    train_writer = tf.summary.FileWriter('./exo_logdir/train', g.loss.graph)
    val_writer = tf.summary.FileWriter('./exo_logdir/val', g.loss.graph)   
    
    ctr = 0
    
    #loading exogenous data points
    exo = np.load("exogenous_jan.npy")
    
    for i in range(1, 71, 5):  
        
        x_closeness = []
        x_period = []
        x_trend = []
        y = []
        X = []
        
        for file_no in range(i, i+5):
            with h5py.File("output_files/xcloseness_"+str(file_no)+".h5", 'r') as hf:
                x_closeness += hf["xcloseness_"+str(file_no)][:].tolist()
            with h5py.File("output_files/xperiod_"+str(file_no)+".h5", 'r') as hf:
                x_period += hf["xperiod_"+str(file_no)][:].tolist()         
            with h5py.File("output_files/xtrend_"+str(file_no)+".h5", 'r') as hf:
                x_trend += hf["xtrend_"+str(file_no)][:].tolist()  
            with h5py.File("output_files/ydata_"+str(file_no)+".h5", 'r') as hf:
                y += hf["ydata_"+str(file_no)][:].tolist()               
            print "Loaded file {}".format(file_no)
         
            
        x_closeness = np.array(x_closeness)  
        x_period = np.array(x_period)  
        x_trend = np.array(x_trend)  

        x_closeness = np.transpose(np.squeeze(x_closeness), (0, 2, 3, 1))
        x_period = np.transpose(np.squeeze(x_period), (0, 2, 3, 1))
        x_trend = np.transpose(np.squeeze(x_trend), (0, 2, 3, 1))
      
              
        selected_exo = exo[ctr:ctr+x_closeness.shape[0], :] 
        ctr += x_closeness.shape[0]
        print "exo ", selected_exo.shape
      
        print np.amax(selected_exo)
        print "closeness ", x_closeness.shape
        
        #print selected_exo[0].tolist()
        
        for j in range(x_closeness.shape[0]):
            X.append([x_closeness[j].tolist(), x_period[j].tolist(), x_trend[j].tolist(), selected_exo[j].tolist()])
    
        
        print len(X)
        train_index = int(round((0.8*len(X)),0))
        xtrain = X[:train_index]
        ytrain = y[:train_index]
        xtest = X[train_index:]
        ytest = y[train_index:]


        #print (xtrain[0:3])
        xtrain = np.array(xtrain)
        ytrain = np.array(ytrain)
        xtest = np.array(xtest)
        ytest = np.array(ytest)
        train_batch_generator = batch_generator(xtrain, ytrain, param.batch_size)
        test_batch_generator = batch_generator(xtest, ytest, param.batch_size)

        print("Start learning ..... ")
        
        #sv = tf.train.Supervisor(graph=g.graph, logdir=param.logdir) 


        with tf.Session(graph=g.graph) as sess:
            sess.run(tf.global_variables_initializer())        
            # restoring model to train on next batch of files from second batch onwards            
            if (i > 1):
                g.saver.restore(sess, param.model_path+"/current")
            for epoch in range(param.num_epochs):            
                loss_train = 0
                loss_val = 0
                print("epoch: {}\t".format(epoch), )

                # Training
                num_batches = xtrain.shape[0] // param.batch_size
                for b in tqdm(range(num_batches)):
                    #print ("before")
                    x_batch, y_batch = next(train_batch_generator)
                    #print ("after")
                    
                    
                    x_closeness = np.array(x_batch[:, 0].tolist())
                    x_period = np.array(x_batch[:, 1].tolist())
                    x_trend = np.array(x_batch[:, 2].tolist())
                    exogenous = np.array(x_batch[:, 3].tolist())
                    
                    #print x_closeness.shape
                    #print x_period.shape
                    #print x_trend.shape
                    #print ("startttt")
                    
                    loss_tr, x_res, _, summary = sess.run([g.loss, g.x_res, g.optimizer, g.merged],
                                                        feed_dict={g.c_tec: x_closeness,
                                                                   g.p_tec: x_period,
                                                                   g.t_tec: x_trend,
                                                                   g.output_tec: y_batch,
                                                                   g.exogenous: exogenous})
                    #print x_res.shape
                    #print x_res[0]
                    #print ("endd")                                               
                    #accuracy_train += acc
                    loss_train = loss_tr * param.delta + loss_train * (1 - param.delta)
                    train_writer.add_summary(summary, b + num_batches * epoch)
                #accuracy_train /= num_batches

                # testing
                num_batches = xtest.shape[0] // param.batch_size
                for b in tqdm(range(num_batches)):
                    x_batch, y_batch = next(test_batch_generator)
                    
                    
                    x_closeness = np.array(x_batch[:, 0].tolist())
                    x_period = np.array(x_batch[:, 1].tolist())
                    x_trend = np.array(x_batch[:, 2].tolist())
                    exogenous = np.array(x_batch[:, 3].tolist())
                    
                    loss_v, summary = sess.run([g.loss, g.merged],
                                                        feed_dict={g.c_tec: x_closeness,
                                                                   g.p_tec: x_period,
                                                                   g.t_tec: x_trend,
                                                                   g.output_tec: y_batch,
                                                                   g.exogenous: exogenous})
                    #accuracy_val += acc
                    loss_val += loss_v
                    val_writer.add_summary(summary, b + num_batches * epoch)
                #accuracy_val /= num_batches
                if(num_batches != 0):
                    loss_val /= num_batches

                print("loss: {:.3f}, val_loss: {:.3f}".format(loss_train, loss_val))
                if (epoch % 10 == 0):
                    g.saver.save(sess, param.model_path+"/epoch_{}_file{}".format(epoch, i))            
            g.saver.save(sess, param.model_path+"/current")
    train_writer.close()
    val_writer.close()
    print("Run 'tensorboard --logdir=./exo_logdir' to checkout tensorboard logs.")
