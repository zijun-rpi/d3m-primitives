"""
Created on Mon Apr 22 15:31:18 2019

@author: zijun
"""

import os
from d3m import container
#from collections import OrderedDict
#from common_primitives import utils as comUtils
from d3m.metadata import base as metadata_base
from common_primitives.dataset_to_dataframe import DatasetToDataFramePrimitive
from common_primitives import column_parser
#from common_primitives import dataset_remove_columns
from common_primitives import construct_predictions
from common_primitives import compute_scores
from common_primitives import extract_columns_semantic_types

from rpi_d3m_primitives.S2TMBplus import S2TMBplus

import d3m.primitives.data_cleaning.imputer as Imputer
import d3m.primitives.classification.random_forest as RF

# Classification
dataset_name = '1491_one_hundred_plants_margin'


print('\nLoad Dataset')   
path = os.path.join('/home/zijun/Dropbox/Project/DARPA-D3M-project/D3Mdatasets-phase1/', dataset_name,'TRAIN/dataset_TRAIN/datasetDoc.json')
dataset = container.Dataset.load('file://{uri}'.format(uri=path))

target_index = dataset.metadata.query(('learningData', metadata_base.ALL_ELEMENTS))['dimension']['length']-1
dataset.metadata = dataset.metadata.add_semantic_type(('learningData', metadata_base.ALL_ELEMENTS, target_index), 'https://metadata.datadrivendiscovery.org/types/Target')
dataset.metadata = dataset.metadata.add_semantic_type(('learningData', metadata_base.ALL_ELEMENTS, target_index), 'https://metadata.datadrivendiscovery.org/types/TrueTarget')
dataset.metadata = dataset.metadata.remove_semantic_type(('learningData', metadata_base.ALL_ELEMENTS, target_index), 'https://metadata.datadrivendiscovery.org/types/Attribute')

print('\nDataset to Dataframe')
hyperparams_class = DatasetToDataFramePrimitive.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
primitive = DatasetToDataFramePrimitive(hyperparams=hyperparams_class.defaults())
call_metadata = primitive.produce(inputs=dataset)
dataframe = call_metadata.value

print('\nColumn Parser')
hyperparams_class = column_parser.ColumnParserPrimitive.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
primitive = column_parser.ColumnParserPrimitive(hyperparams=hyperparams_class.defaults())
dataframe = primitive.produce(inputs=dataframe).value

print('\nExtract Attributes')
hyperparams_class = extract_columns_semantic_types.ExtractColumnsBySemanticTypesPrimitive.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
primitive = extract_columns_semantic_types.ExtractColumnsBySemanticTypesPrimitive(hyperparams=hyperparams_class.defaults().replace({'semantic_types': ['https://metadata.datadrivendiscovery.org/types/Attribute']}))
call_metadata = primitive.produce(inputs=dataframe)
trainD = call_metadata.value

print('\nExtract Targets')
hyperparams_class = extract_columns_semantic_types.ExtractColumnsBySemanticTypesPrimitive.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
primitive = extract_columns_semantic_types.ExtractColumnsBySemanticTypesPrimitive(hyperparams=hyperparams_class.defaults().replace({'semantic_types':['https://metadata.datadrivendiscovery.org/types/SuggestedTarget']}))
call_metadata = primitive.produce(inputs=dataframe)
trainL = call_metadata.value


print ('\nLoad testing dataset') 
path = os.path.join('/home/zijun/Dropbox/Project/DARPA-D3M-project/D3Mdatasets-phase1/', dataset_name,'TEST/dataset_TEST/datasetDoc.json')
dataset = container.Dataset.load('file://{uri}'.format(uri=path))

dataset.metadata = dataset.metadata.add_semantic_type(('learningData', metadata_base.ALL_ELEMENTS, target_index), 'https://metadata.datadrivendiscovery.org/types/Target')
dataset.metadata = dataset.metadata.add_semantic_type(('learningData', metadata_base.ALL_ELEMENTS, target_index), 'https://metadata.datadrivendiscovery.org/types/TrueTarget')
dataset.metadata = dataset.metadata.remove_semantic_type(('learningData', metadata_base.ALL_ELEMENTS, target_index), 'https://metadata.datadrivendiscovery.org/types/Attribute')

print('\nDataset to Dataframe')
hyperparams_class = DatasetToDataFramePrimitive.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
primitive = DatasetToDataFramePrimitive(hyperparams=hyperparams_class.defaults())
call_metadata = primitive.produce(inputs=dataset)
dataframe = call_metadata.value


print('\nColumn Parser')
hyperparams_class = column_parser.ColumnParserPrimitive.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
primitive = column_parser.ColumnParserPrimitive(hyperparams=hyperparams_class.defaults())
dataframe = primitive.produce(inputs=dataframe).value


print('\nExtract Attributes')
hyperparams_class = extract_columns_semantic_types.ExtractColumnsBySemanticTypesPrimitive.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
primitive = extract_columns_semantic_types.ExtractColumnsBySemanticTypesPrimitive(hyperparams=hyperparams_class.defaults().replace({'semantic_types': ['https://metadata.datadrivendiscovery.org/types/Attribute']}))
call_metadata = primitive.produce(inputs=dataframe)
testD = call_metadata.value


print('\nExtract Suggested Target')
hyperparams_class = extract_columns_semantic_types.ExtractColumnsBySemanticTypesPrimitive.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
primitive = extract_columns_semantic_types.ExtractColumnsBySemanticTypesPrimitive(hyperparams=hyperparams_class.defaults().replace({'semantic_types': ['https://metadata.datadrivendiscovery.org/types/SuggestedTarget']}))
call_metadata = primitive.produce(inputs=dataframe)
testL = call_metadata.value


print('\nGet Target Name')
column_metadata = testL.metadata.query((metadata_base.ALL_ELEMENTS, 0))
TargetName = column_metadata.get('name',[])

print('S2TMB feature selection')
nbins = 19 #nbins
hyperparams_class = S2TMBplus.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
FSmodel = S2TMBplus(hyperparams=hyperparams_class.defaults().replace({'nbins':nbins}))
FSmodel.set_training_data(inputs=trainD, outputs=trainL)        
FSmodel.fit()
print('\nSelected Feature Index')
print(FSmodel._index)
print('\n')
trainD = FSmodel.produce(inputs=trainD) 
trainD = trainD.value

print('\nSubset of testing data')
testD = FSmodel.produce(inputs=testD)
testD = testD.value

##================================================================================
print('\nImpute trainD')
hyperparams_class = Imputer.SKlearn.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
Imputer_primitive = Imputer.SKlearn(hyperparams=hyperparams_class.defaults().replace({'strategy':'most_frequent'}))
Imputer_primitive.set_training_data(inputs=trainD)
Imputer_primitive.fit()
trainD = Imputer_primitive.produce(inputs=trainD).value

print('\nImpute testD')
testD = Imputer_primitive.produce(inputs=testD).value
    
##===============================================================================================
print('\nRandom Forest')
n_estimators = 28
hyperparams_class = RF.SKlearn.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
RF_primitive = RF.SKlearn(hyperparams=hyperparams_class.defaults().replace({'n_estimators':n_estimators}))
RF_primitive.set_training_data(inputs=trainD, outputs=trainL)
RF_primitive.fit()
predictedTargets = RF_primitive.produce(inputs=testD)
predictedTargets = predictedTargets.value


##================================================================================================
print('\nConstruct Predictions')
hyperparams_class = construct_predictions.ConstructPredictionsPrimitive.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
construct_primitive = construct_predictions.ConstructPredictionsPrimitive(hyperparams=hyperparams_class.defaults())
call_metadata = construct_primitive.produce(inputs=predictedTargets, reference=dataframe)
dataframe = call_metadata.value

print('\ncompute scores')
path = os.path.join('/home/zijun/Dropbox/Project/DARPA-D3M-project/D3Mdatasets-phase1/', dataset_name, 'SCORE/dataset_TEST/datasetDoc.json')
dataset = container.Dataset.load('file://{uri}'.format(uri=path))

dataset.metadata = dataset.metadata.add_semantic_type(('learningData', metadata_base.ALL_ELEMENTS, target_index), 'https://metadata.datadrivendiscovery.org/types/Target')
dataset.metadata = dataset.metadata.add_semantic_type(('learningData', metadata_base.ALL_ELEMENTS, target_index), 'https://metadata.datadrivendiscovery.org/types/TrueTarget')

hyperparams_class = compute_scores.ComputeScoresPrimitive.metadata.query()['primitive_code']['class_type_arguments']['Hyperparams']
metrics_class = hyperparams_class.configuration['metrics'].elements
primitive = compute_scores.ComputeScoresPrimitive(hyperparams=hyperparams_class.defaults().replace({
            'metrics': [metrics_class({
                'metric': 'F1_MACRO',
                'pos_label': None,
                'k': None,
            })],
        }))
scores = primitive.produce(inputs=dataframe, score_dataset=dataset).value


print(scores)
#  F1_MACRO  0.767416

#print('\nSave file')
#os.mkdir('/output/predictions/e7239570-bb9d-464b-aa5b-a0f7be958dc0')
#output_path = os.path.join('/output','predictions','e7239570-bb9d-464b-aa5b-a0f7be958dc0','predictions.csv')
#with open(output_path, 'w') as outputFile:
#    dataframe.to_csv(outputFile, index=False,columns=['d3mIndex', TargetName])
