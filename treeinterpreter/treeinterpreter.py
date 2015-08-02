# -*- coding: utf-8 -*-
import numpy as np

import sys
sys.path.insert(0, r'c:\projects\scikit-learn-master\scikit-learn\build\lib.win32-2.7')
sys.path.insert(0, r'c:\projects\scikit-learn-master\build\lib.win-amd64-2.7')

from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier, _tree
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import RandomForestClassifier


def get_tree_paths(tree, node_id, parent=None, depth=0):
    """
    Returns all paths through the tree as list of node_ids
    """
    if node_id == _tree.TREE_LEAF:
        raise ValueError("Invalid node_id %s" % _tree.TREE_LEAF)

    left_child = tree.children_left[node_id]
    right_child = tree.children_right[node_id]

    if left_child != _tree.TREE_LEAF:
        left_paths = get_tree_paths(tree, left_child, parent=node_id,
                                    depth=depth + 1)
        right_paths = get_tree_paths(tree, right_child,  parent=node_id,
                                     depth=depth + 1)

        for p in left_paths:
            p.append(node_id)
        for p in right_paths:
            p.append(node_id)
        paths = left_paths + right_paths
    else:
        paths = [[node_id]]
    return paths


def predict_tree(model, X):
    # Only single out response variable supported,
    if model.n_outputs_ > 1:
        raise ValueError("Multilabel classification trees not supported")
    leaves = model.apply(X)
    paths = get_tree_paths(model.tree_, 0)

    for path in paths:
        path.reverse()

    contributions = np.zeros(X.shape)
    biases = np.zeros(X.shape[0])

    if type(model) == DecisionTreeRegressor:
        for row, leaf in enumerate(leaves):
            for path in paths:
                if leaf == path[-1]:
                    break
            biases[row] = model.tree_.value[path[0]]
            contribs = np.zeros(X.shape[1])
            for i in range(len(path) - 1):
                contrib = model.tree_.value[path[i+1]] - \
                          model.tree_.value[path[i]]
                contribs[model.tree_.feature[path[i]]] += contrib
            contributions[row] = contribs
            direct_prediction = model.tree_.value.take(
                leaves, axis=0, mode='clip').reshape(X.shape[0], 1)[:, 0]
    elif type(model) == DecisionTreeClassifier:        
        # remove the single-dimensional inner arrays
        values = model.tree_.value.squeeze()
        # scikit stores category counts, we turn them into probabilities
        normalizer = values.sum(axis=1)[:, np.newaxis]
        normalizer[normalizer == 0.0] = 1.0
        values /= normalizer

        biases = np.zeros((X.shape[0], model.n_classes_))
        contributions = np.zeros((X.shape[0],
                                  X.shape[1], model.n_classes_))

        for row, leaf in enumerate(leaves):
            for path in paths:
                if leaf == path[-1]:
                    break
            biases[row] = values[path[0]]
            contribs = np.zeros((X.shape[1], model.n_classes_))

            for i in range(len(path) - 1):
                contrib = values[path[i+1]] - \
                          values[path[i]]
                contribs[model.tree_.feature[path[i]]] += contrib
            contributions[row] = contribs
            direct_prediction = values[leaves]

    else:
        raise ValueError("Wrong model type. Base learner needs to be \
            DecisionTreeClassifier or DecisionTreeRegressor.")

    return direct_prediction, biases, contributions


def predict_forest(model, X):
    biases = []
    contributions = []
    predictions = []
    for tree in model.estimators_:
        pred, bias, contribution = predict_tree(tree, X)
        biases.append(bias)
        contributions.append(contribution)
        predictions.append(pred)
    return (np.mean(predictions, axis=0), np.mean(biases, axis=0),
            np.mean(contributions, axis=0))
