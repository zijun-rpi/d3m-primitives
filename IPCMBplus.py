# with input in the DataFrame format
# update metadata of the dataset

import os, sys
from typing import Union, Dict
import scipy.io
import numpy as np
from sklearn import preprocessing
from common_primitives import utils
from d3m import container
from d3m.metadata import base as metadata_base
from d3m.metadata import hyperparams
from d3m.metadata import params
from d3m.primitive_interfaces.supervised_learning import SupervisedLearnerPrimitiveBase
from d3m.primitive_interfaces import base
from d3m.primitive_interfaces.base import CallResult
import rpi_d3m_primitives
from rpi_d3m_primitives.featSelect.Feature_Selector_model import IPCMB
from rpi_d3m_primitives.featSelect.RelationSet import RelationSet



Inputs = container.DataFrame
Outputs = container.DataFrame

__all__ = ('IPCMBplus',)

class Params(params.Params):
    pass


class Hyperparams(hyperparams.Hyperparams):
    threshold = hyperparams.Hyperparameter[Union[int, float]](
        default=0.02,
        description="A non-negative threshold for independence test using mutual information. The number of selected features will be larger if the hyper-parameter is closer to zero.",
        semantic_types=['https://metadata.datadrivendiscovery.org/types/TuningParameter']
    )


class IPCMBplus(SupervisedLearnerPrimitiveBase[Inputs, Outputs, Params, Hyperparams]):
    """
    A primitive which selects a set of features condition on which the target is independent of other features. An implementation of "identity parent-children markov blanket discovery" method.
    """

    metadata = metadata_base.PrimitiveMetadata({
        'id': '9d1a2e58-5f97-386c-babd-5a9b4e9b6d6c',
        'version': '2.1.5',
        'name': 'IPCMBplus feature selector',
        'keywords': ['Markov Blanket Discovery','Feature Selection'],
        'description': 'This algorithm is an implementation of the identity Parent-Children Markov Blanket Discovery method. Nodes in the learned Markov Blanket will be the selected features',
        'source': {
            'name': rpi_d3m_primitives.__author__,
            'contact': 'mailto:cuiz3@rpi.edu',
            'uris': [
                'https://github.com/zijun-rpi/d3m-primitives/blob/master/IPCMBplus.py',
                'https://github.com/zijun-rpi/d3m-primitives.git'
                ]
        },
        'installation':[
            {
                'type': metadata_base.PrimitiveInstallationType.PIP,
                'package': 'rpi_d3m_primitives',
	            'version': rpi_d3m_primitives.__version__
            }
        ],
        'python_path': 'd3m.primitives.feature_selection.identity_parentchildren_markov_blanket.ManualRPI',
        'algorithm_types': [
            metadata_base.PrimitiveAlgorithmType.MINIMUM_REDUNDANCY_FEATURE_SELECTION
        ],
        'primitive_family': metadata_base.PrimitiveFamily.FEATURE_SELECTION,
        'preconditions': [
            "NO_CATEGORICAL_VALUES"
        ]
    })


    def __init__(self, *, hyperparams: Hyperparams, random_seed: int = 0, docker_containers: Union[Dict[str, base.DockerContainer]] = None) -> None:
        super().__init__(hyperparams=hyperparams, random_seed=random_seed, docker_containers=docker_containers)
        self._index = None
        self._problem_type = 'classification'
        self._training_inputs = None
        self._training_outputs = None
        self._fitted = False

    def set_training_data(self, *, inputs: Inputs, outputs: Outputs) -> None:
        # set training labels
        [m,n] = inputs.shape
        self._training_outputs = np.zeros((m,))
        temp = list(outputs.iloc[:,0].values)
        for i in np.arange(len(temp)):
            self._training_outputs[i] = float(temp[i])
        
        # set problem type
        metadata = outputs.metadata
        column_metadata = metadata.query((metadata_base.ALL_ELEMENTS, 0))
        semantic_types = column_metadata.get('semantic_types', [])
        if 'https://metadata.datadrivendiscovery.org/types/CategoricalData' in semantic_types:
            self._problem_type = 'classification'
        else:
            self._problem_type = 'regression'
            
        # convert cateforical values to numerical values in training data
        metadata = inputs.metadata
        [m,n] = inputs.shape
        self._training_inputs = np.zeros((m,n))
        for column_index in metadata.get_elements((metadata_base.ALL_ELEMENTS,)):
            if column_index is metadata_base.ALL_ELEMENTS: 
                continue
            column_metadata = metadata.query((metadata_base.ALL_ELEMENTS, column_index))
            semantic_types = column_metadata.get('semantic_types', [])
            if 'https://metadata.datadrivendiscovery.org/types/CategoricalData' in semantic_types:
                LE = preprocessing.LabelEncoder()
                LE = LE.fit(inputs.iloc[:,column_index])
                self._training_inputs[:,column_index] = LE.transform(inputs.iloc[:,column_index])  
            else:
                temp = list(inputs.iloc[:, column_index].values)
                for i in np.arange(len(temp)):
                    if bool(temp[i]):
                        self._training_inputs[i,column_index] = float(temp[i])
                    else:
                        self._training_inputs[i,column_index] = 'nan'
        self._fitted = False


    def fit(self, *, timeout: float = None, iterations: int = None) -> None:
        if self._fitted:
            return CallResult(None)

        if self._training_inputs.any() == None or self._training_outputs.any() == None: 
            raise ValueError('Missing training data, or missing values exist.')

        Trainset = RelationSet(self._training_inputs, self._training_outputs.reshape(-1, 1))
        Trainset.impute()
        discTrainset = RelationSet(self._training_inputs, self._training_outputs.reshape(-1, 1))
        discTrainset.impute()
        discTrainset.discretize()
        model = IPCMB(Trainset, discTrainset,self._problem_type)
        index = model.select_features(thres=self.hyperparams['threshold'])
        self._index = []
        [m, ] = index.shape
        for ii in np.arange(m):
            self._index.append(index[ii].item())
        self._fitted = True

        return CallResult(None)


    def produce(self, *, inputs: Inputs, timeout: float = None, iterations: int = None) -> base.CallResult[Outputs]:  # inputs: m x n numpy array
        if self._fitted:
            output = inputs.iloc[:, self._index]
            output.metadata = utils.select_columns_metadata(inputs.metadata, columns=self._index)
            return CallResult(output)
        else:
            raise ValueError('Model should be fitted first.')


    def get_params(self) -> None:
        pass


    def set_params(self) -> None:
        pass

