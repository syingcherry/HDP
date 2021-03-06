# __author__ = 'WeiFu'
from __future__ import print_function, division
import math
from utility import *
from scipy import stats
import numpy as np
import networkx as nx
from Sample import *

def transform(d, selected=[]):
  """
  the data will be stored by column, not by instance
  :param d : data
  :type d: o
  :return col: the data grouped by each column
  :type col: dict
  """
  col = {}
  for val, attr in zip(d["data"], d["attr"]):
    if len(selected) == 0:
      col[attr] = val
    elif attr in selected:
      col[attr] = val
  return col
  # for row in d["data"]:
  # for attr, cell in zip(d["attr"][:-1], row[:-1]):  # exclude last columm, $bug
  #     if len(selected) != 0 and attr not in selected:  # get rid of name, version columns.
  #       continue  # if this is for feature selected data, just choose those features.
  #     col[attr] = col.get(attr, []) + [cell]
  # return col


def maximumWeighted(match, target_lst, source_lst):
  """
  using max_weighted_bipartite to select a group of matched metrics
  :param match : matched metrics with p values, key is the tuple of matched metrics
  :type match : dict
  :param target_lst : matched target metrics
  :type target_lst: list
  :param source_lst : matched source metcis
  :type source_lst: list
  :return : matched metrics as well as corresponding values
  :rtype: class o
  """
  value = 0
  attr_source, attr_target = [], []
  G = nx.Graph()
  for key, val in match.iteritems():
    G.add_edge(key[0] + "source", key[1] + "target", weight=val)  # add suffix to make it unique
  result = nx.max_weight_matching(G)
  for key, val in result.iteritems():  # in Results, (A:B) and (B:A) both exist
    if key[:-6] in source_lst and val[:-6] in target_lst \
        and (key[:-6], val[:-6]) in match : # get rid of (A:B) exists but (B:A) not
      if key[:-6] in attr_source and val[:-6] in attr_target and\
        attr_source.index(key[:-6]) == attr_target.index(val[:-6]):
        continue # this is (A:B) already in attr_source and attr_target
      attr_target.append(val[:-6])
      attr_source.append(key[:-6])
      value += match[(key[:-6], val[:-6])]
  # pdb.set_trace()
  return o(score=value, attr_source=attr_source, attr_target=attr_target)


def KStest(d_source, d_target, features, cutoff=0.05):
  """
  Kolmogorov-Smirnov Test
  :param d_source : source data
  :type d_source : o
  :param d_target: target data
  :type d_target: os
  :param features: features selected for the source data set
  :type features : list
  :return : results of maximumWeighted
  :rtype: o
  """
  match = {}
  source = transform(d_source, features)
  target = transform(d_target)
  target_lst, source_lst = [], []
  # test = autoclass('org.apache.commons.math3.stat.inference.KolmogorovSmirnovTest')()
  for tar_feature, val1 in target.iteritems():
    for sou_feature, val2 in source.iteritems():
      # result = test.kolmogorovSmirnovTest(val1, val2) # this is the java version of KS test
      temp = stats.ks_2samp(val1, val2)
      result = temp[1]
      if result > cutoff:
        # match[sou] = match.get(sou,[])+[(tar,result[1])]
        match[(sou_feature, tar_feature)] = result
        if tar_feature not in target_lst:
          target_lst.append(tar_feature)
        if sou_feature not in source_lst:
          source_lst.append(sou_feature)
  if len(match) < 1:
    return o(score=0)
  return maximumWeighted(match, target_lst, source_lst)


def attributeSelection(data):
  feature_dict = {}
  for key, lst in data.iteritems():
    for source in lst:
      source_name = source["name"]
      A = loadWekaData(source_name)
      A_selected_index = featureSelection(A, int(int(A.classIndex()) * 0.15))
      features_list = [str(attr)[str(attr).find("@attribute") + len("@attribute") + 1:str(attr).find("numeric") - 1]
                       for i, attr in enumerate(enumerateToList(A.enumerateAttributes())) if i in A_selected_index]
      feature_dict[source_name] = features_list
  return feature_dict


def selectRows(old_data, option):
  """
  to do supervised or unsupervised instance selection
  :param data: the original data
  :type data : o
  :param option: options to indicate kind of instance selection
  :type option: list

  """
  if len(option) == 0: return old_data
  i = 0
  while i<=4:
    if (option[i] == "-S" and option[i + 1] == "S") or (option[i] == "-T" and option[i + 1] == "S"):
      if isinstance(option[option.index("-N") + 1], int):
        return selectInstances(old_data, option)
      else:
        raise ValueError("Should indicate an int number of intances")
    i += 2
  return old_data


def KSanalyzer(source_src, target_src, option=[], cutoff=0.05):
  """
  for each target data set, find a best source data set in terms of p-values
  :param source_src : src of KS source data sets
  :type source_src: str
  :param target_src: src of KS target data sets
  :type target_src : src
  :param option: set the Large or small data set for KS test, here small means using unsupervised or supervised methods to select rows
  :type option: list
  :return pairs of matched data
  :rtype: list
  """
  target_data = read(target_src)
  source_data = read(source_src)
  best_pairs = []
  selected_features = attributeSelection(source_data)
  for target_group, targetlst in target_data.iteritems():
    for target in targetlst:
      for source_group, sourcelst in source_data.iteritems():
        if target_group != source_group:
          for source in sourcelst:
            source_name = source["name"]
            target_name = target["name"]
            if len(option) >= 2 and "-EPV" not in option:  # select some rows for KS test, when no EPV
              if "-S" in option and option[option.index("-S") + 1] == "S" :
                source = selectInstances(source, option)
              if "-T" in option and option[option.index("-T") + 1] == "S" :
                target = selectInstances(target, option)
            X = KStest(source, target, selected_features[source_name])\
              .update(source_src=source_name,group=source_group,target_name=target_name[target_name.rindex("/")+1:]) # source is the src, target is the name of data file
            if X["score"] > cutoff:
              best_pairs.append(X)
  return best_pairs


def call(source_src, target_src, source_attr, target_attr):
  """
  call weka to perform learning and testing
  :param train: src of training data
  :type train: str
  :param test: src of testing data
  :type test: str
  :param source_attr: matched feature for training data set
  :type source_attr: list
  :param target_attr: matched feature for testing data set
  :type target_attr: list
  :return ROC area value
  :rtype: list
  """
  r = round(wekaCALL(source_src, target_src, source_attr, target_attr, True), 3)
  if not math.isnan(r):
    return [r]
  else:
    return []


def hdp(option, target, source_target_match):
  """
   source_target_match = KSanalyzer()
  :param option : options for small or large datasets
  :type option : list
  :param target_src : src of test(target) data set
  :type target_src : str
  :param source_target_match : matched source and target data test
  :type source_target_match: list
  :return: value of ROC area
  :rtype: list
  """
  result = []
  for i in source_target_match:
    if i.target_name == target:
      source_attr = i.attr_source
      target_attr = i.attr_target
      # pdb.set_trace()
      # test = chops(i, i.source_src,source_attr)
      # pdb.set_trace()
      result.append(o(result=call(i.source_src, "./exp/train.arff", source_attr, target_attr), source_src=i.source_src))
      result.append(o(result=call(i.source_src, "./exp/test.arff", source_attr, target_attr), source_src=i.source_src))
  return result


def testEQ():
  def tofloat(lst):
    for x in lst:
      try:
        yield float(x)
      except ValueError:
        yield x[:-1]

  target_src = "./dataset/Relink/apache.arff"
  source_src = "./dataset/AEEEM/EQ.arff"

  d = open("./datasetcsv/AEEEM/EQ.csv", "r")
  content = d.readlines()
  attr = content[0].split(",")
  inst = [list(tofloat(row.split(","))) for row in content[1:]]
  d1 = o(name="./datasetcsv/AEEEM/EQ.csv", attr=attr, data=inst)

  d = open("./datasetcsv/Relink/apache.csv", "r")
  content = d.readlines()
  attr = content[0].split(",")
  inst = [list(tofloat(row.split(","))) for row in content[1:]]
  d2 = o(name="./datasetcsv/Relink/apache.csv", attr=attr, data=inst)
  Result = KStest(d1, d2, source_src)
  print(Result)
  # pdb.set_trace()
  print("DONE")


if __name__ == "__main__":
  random.seed(1)
  np.random.seed(1)
  # wpdp()
  # KSanalyzer()
  # wekaCALL()
  # filter()
  # cpdp()
  # readarff()
  testEQ()
