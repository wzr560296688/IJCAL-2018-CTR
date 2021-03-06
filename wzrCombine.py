import pandas as pd
import numpy as np
from sklearn.decomposition import TruncatedSVD
from FeatExtract import *
from utils import *
from divideCate import *
from sklearn.feature_extraction.text import TfidfVectorizer
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss
from sklearn import preprocessing
import warnings
warnings.filterwarnings("ignore")
import time
from preprocess import pre

def timestamp_datetime(value):
    format = '%Y-%m-%d %H:%M:%S'
    value = time.localtime(value)
    dt = time.strftime(format, value)
    return dt


def base_process(data):
    lbl = preprocessing.LabelEncoder()
    print("---------------------------------------------------------time---------------------------")
    data['realtime'] = data['context_timestamp'].apply(timestamp_datetime)
    data['realtime'] = pd.to_datetime(data['realtime'])
    data['day'] = data['realtime'].dt.day
    data['hour'] = data['realtime'].dt.hour
    print(
        '--------------------------------------------------------------item--------------------------------------------------------------')
    data['len_item_category'] = data['item_category_list'].map(lambda x: len(str(x).split(';')))
    data['len_item_property'] = data['item_property_list'].map(lambda x: len(str(x).split(';')))
    for i in range(1, 3):
        data['item_category_list' + str(i)] = lbl.fit_transform(data['item_category_list'].map(
            lambda x: str(str(x).split(';')[i]) if len(str(x).split(';')) > i else ''))
    for i in range(10):
         data['item_property_list' + str(i)] = lbl.fit_transform(data['item_property_list'].map(lambda x: str(str(x).split(';')[i]) if len(str(x).split(';')) > i else ''))
    for col in ['item_id', 'item_brand_id', 'item_city_id']:
        data[col] = lbl.fit_transform(data[col])
    print(
        '--------------------------------------------------------------user--------------------------------------------------------------')
    for col in ['user_id']:
        data[col] = lbl.fit_transform(data[col])
    print('user 0,1 feature')
    data['gender0'] = data['user_gender_id'].apply(lambda x: 1 if x == -1 else 2)
    data['age0'] = data['user_age_level'].apply(lambda x: 1 if x == 1004 | x == 1005 | x == 1006 | x == 1007  else 2)
    data['occupation0'] = data['user_occupation_id'].apply(lambda x: 1 if x == -1 | x == 2003  else 2)
    data['star0'] = data['user_star_level'].apply(lambda x: 1 if x == -1 | x == 3000 | x == 3001  else 2)
    print(
        '--------------------------------------------------------------context--------------------------------------------------------------')
    user_query_day = data.groupby(['user_id', 'day']).size(
    ).reset_index().rename(columns={0: 'user_query_day'})
    data = pd.merge(data, user_query_day, 'left', on=['user_id', 'day'])
    user_query_day_hour = data.groupby(['user_id', 'day', 'hour']).size().reset_index().rename(
        columns={0: 'user_query_day_hour'})
    data = pd.merge(data, user_query_day_hour, 'left',
                    on=['user_id', 'day', 'hour'])

    data['len_predict_category_property'] = data['predict_category_property'].map(lambda x: len(str(x).split(';')))
    for i in range(5):
        data['predict_category_property' + str(i)] = lbl.fit_transform(data['predict_category_property'].map(
            lambda x: str(str(x).split(';')[i]) if len(str(x).split(';')) > i else ''))
    print('context 0,1 feature')
    data['context_page0'] = data['context_page_id'].apply(
        lambda x: 1 if x == 4001 | x == 4002 | x == 4003 | x == 4004 | x == 4007  else 2)
    print(
        '--------------------------------------------------------------shop--------------------------------------------------------------')
    for col in ['shop_id']:
        data[col] = lbl.fit_transform(data[col])
    data['shop_score_delivery0'] = data['shop_score_delivery'].apply(lambda x: 0 if x <= 0.98 and x >= 0.96  else 1)
    divdeByCate(data,"second_cate")
    return data

def process_prop(data, attrName):
    count_vec = TfidfVectorizer()
    data_ip = count_vec.fit_transform(data[attrName])
    print(data_ip)
    train_index = data[data['day']<24].index
    ip_train = data_ip[list(train_index),:]
    train_label = data.loc[data['day']<24,'is_trade']
    test_index = data[data['day']==24].index
    ip_test = data_ip[list(test_index),:]
    test_label = data.loc[data['day']==24,'is_trade']
    lgb0 = lgb.LGBMClassifier(
        objective='binary',
        num_leaves=24,
        depth=2,
        learning_rate=0.05,
        seed=2018,
        colsample_bytree=0.3,
        subsample=0.8,
        n_jobs=10,
        n_estimators=500)
    lgb0.fit(ip_train, train_label, eval_set=[(ip_test, test_label)],
                         early_stopping_rounds=10)
    data["text_{0}".format(attrName)] = lgb0.predict_proba(count_vec.fit_transform(data[attrName]))[:, 1]
    return data
def svdSpareMat(data,attrName):
    count_vec = TfidfVectorizer()
    data_ip = count_vec.fit_transform(data[attrName])
    train_index = data[data['day']<24].index
    ip_train = data_ip[list(train_index),:]
    svd = TruncatedSVD(n_components=80,n_iter = 90)
    svd.fit(ip_train)
    print(svd.explained_variance_ratio_)
def map_hour(x):
    if (x>=7)&(x<=12):
        return 1
    elif (x>=13)&(x<=20):
        return 2
    else:
        return 3

def lgbCV(train, test):
    col = [c for c in train if
           c not in ['is_trade', 'item_category_list', 'item_property_list', 'predict_category_property', 'instance_id',
                     'context_id', 'realtime', 'context_timestamp','first_cate','second_cate','has_trade',
                     'shop_click_buy_total','page_buy','item_buy','item_brand_buy','item_brand_click','item_shop_click_buy_total',
                     'user_brand_buy','occupation_brand_buy','star_brand_buy','user_click_buy_total',
                     'occupation_item_click_buy_total','occupation_item_click_total',
                     'occupation_brand_buy','occupation_brand_rate','gender_brand_buy','gender_brand_click',
                     'user_click_buy_total','user_click_buy_rate','user_click_total'
                     ]]
    X = train[col]
    y = train['is_trade'].values
    X_tes = test[col]
    y_tes = test['is_trade'].values
    print('Training LGBM model...')
    lgb0 = lgb.LGBMClassifier(
        objective='binary',
        # metric='binary_error',
        num_leaves=35,
        depth=4,
        learning_rate=0.01,
        seed=2018,
        colsample_bytree=0.8,
        # min_child_samples=8,
        subsample=0.9,
        n_estimators=20000)
    lgb_model = lgb0.fit(X, y, eval_set=[(X_tes, y_tes)], categorical_feature=['user_gender_id','gender0','occupation0','star0','age0'], early_stopping_rounds=200)
    best_iter = lgb_model.best_iteration_
    pred = lgb_model.predict_proba(test[col])[:, 1]
    test['pred'] = pred
    test['index'] = range(len(test))
    #processHasTrade(test,"pred")
    # print(test[['is_trade','pred']])
    print(log_loss(test['is_trade'], test['pred']))
    return best_iter

def sub(train, test, best_iter):
    col = [c for c in train if
           c not in ['is_trade', 'item_category_list', 'item_property_list', 'predict_category_property', 'instance_id',
                     'context_id', 'realtime', 'context_timestamp','first_cate','second_cate','has_trade',
                     'shop_click_buy_total','page_buy','item_buy','item_brand_buy','item_brand_click','item_shop_click_buy_total',
                     'user_brand_buy','occupation_brand_buy','star_brand_buy','user_click_buy_total',
                     'occupation_item_click_buy_total','occupation_item_click_total',
                     'occupation_brand_buy','occupation_brand_rate','gender_brand_buy','gender_brand_click',
                     'user_click_buy_total','user_click_buy_rate','user_click_total'
                     ]]
    X = train[col]
    y = train['is_trade'].values
    print('Training LGBM model...')
    lgb0 = lgb.LGBMClassifier(
        objective='binary',
        # metric='binary_error',
        num_leaves=35,
        depth=4,
        learning_rate=0.01,
        seed=2018,
        colsample_bytree=0.8,
        # min_child_samples=8,
        subsample=0.9,
        n_estimators=best_iter)
    lgb_model = lgb0.fit(X, y,categorical_feature=['user_gender_id','gender0','occupation0','star0','age0'] )
    pred = lgb_model.predict_proba(test[col])[:, 1]
    test['predicted_score'] = pred
    #processHasTrade(test,"predicted_score")
    sub1 = test[['instance_id', 'predicted_score']]
    sub=pd.read_csv("te.csv")
    sub=pd.merge(sub,sub1,on=['instance_id'],how='left')
    sub=sub.fillna(0)
    sub[['instance_id', 'predicted_score']].to_csv('result0326.txt',sep=" ",index=False)


if __name__ == "__main__":

    pre()
    online = True
    train = pd.read_csv("tr.csv")
    test = pd.read_csv("te.csv")
    data = pd.concat([train, test])
    data = data.drop_duplicates(subset='instance_id')
    data = base_process(data)
    #data = process_prop(data,"item_property_list")
    #svdSpareMat(data,"item_property_list")
    #data = user_click_comm_level(data) #No obvious change
    #data = comm_extra(data)-   #cause bigger loss
    #data = comm_gender(data)
    data = brand_extra(data) #-Good feature
    data = user_extra(data) #-Good feature
    data = shop_extra(data) #-Good feature
    #data = user_click_comm_level(data)
  #  train= data[(data['day'] >= 18) & (data['day'] <= 23)]
  #  test= data[(data['day'] == 24)]
 #  #train,test = hasTrade(train,test,"item_category_list1")
  #  train,test = user_feat(train,test)
  #  train,test = shop_feat(train,test)#0.085
 #   train,test = context_feat(train,test)
 #   train,test = item_feat(train,test) #0.0815
    #train,test = user_cate_combine(train,test)
    # train,test = item_prop_feat(train,test)
    #train,test = shop_combine(train,test)
    #train,test = brand_combine(train,test)#  +0.001
    #train,test = user_brand(train,test)
    #train,test = user_city(train,test)
    #train,test = user_prop_item(train,test)
   # best_iter = lgbCV(train, test)
   # del train
   # del test
    if(online == True):
        train = data[data.is_trade.notnull()]
        test = data[data.is_trade.isnull()]
        train,test = user_feat(train,test)
        train,test = shop_feat(train,test)#0.085
        train,test = context_feat(train,test)
        train,test = item_feat(train,test) #0.0815
        #train,test = hasTrade(train,test,"item_category_list1")
        #train,test = cateHit(train,test,"item_category_list1")
        #train,test = cateHit(train,test,"item_category_list2")
        sub(train, test, best_iter)
