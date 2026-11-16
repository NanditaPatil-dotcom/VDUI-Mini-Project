import argparse, json, os, time
import numpy as np, pandas as pd, joblib
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
KIND='rf'
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--data',default='airline_satisfaction_cleaned(1).csv'); ap.add_argument('--train-indices',default='train_indices.csv'); ap.add_argument('--test-indices',default='test_indices.csv'); ap.add_argument('--output-dir',default='.'); a=ap.parse_args(); os.makedirs(a.output_dir,exist_ok=True)
 df=pd.read_csv(a.data); tr=pd.read_csv(a.train_indices).row_index.astype(int).to_numpy(); te=pd.read_csv(a.test_indices).row_index.astype(int).to_numpy()
 assert len(np.unique(tr))==len(tr) and len(np.unique(te))==len(te) and set(tr).isdisjoint(set(te)) and set(tr)|set(te)==set(range(len(df)))
 ratings=['Departure and Arrival Time Convenience','Ease of Online Booking','Check-in Service','Online Boarding','Gate Location','On-board Service','Seat Comfort','Leg Room Service','Cleanliness','Food and Drink','In-flight Service','In-flight Wifi Service','In-flight Entertainment','Baggage Handling']; cats=['Gender','Customer Type','Type of Travel','Class']
 X=df.drop(columns=['Satisfaction','satisfaction']).copy(); y=df.Satisfaction.map({'Neutral or Dissatisfied':0,'Satisfied':1}).astype(int)
 for c in ratings: X[c+'_not_applicable']=(X[c]==0).astype('int8'); X[c]=X[c].replace(0,np.nan)
 nums=[c for c in X.columns if c not in cats]; prep=ColumnTransformer([('numeric',Pipeline([('imputer',SimpleImputer(strategy='median'))]),nums),('categorical',Pipeline([('imputer',SimpleImputer(strategy='most_frequent')),('onehot',OneHotEncoder(handle_unknown='ignore'))]),cats)])
 if KIND=='rf':
  from sklearn.ensemble import RandomForestClassifier
  est=RandomForestClassifier(n_estimators=60,max_depth=20,min_samples_split=5,min_samples_leaf=2,max_features='sqrt',max_samples=.70,random_state=42,n_jobs=-1); prefix='random_forest'; name='Random Forest'
 else:
  from xgboost import XGBClassifier
  est=XGBClassifier(n_estimators=350,max_depth=6,learning_rate=.08,subsample=.80,colsample_bytree=.80,min_child_weight=2,reg_lambda=1.0,objective='binary:logistic',eval_metric='logloss',tree_method='hist',random_state=42,n_jobs=4); prefix='boosting'; name='XGBoost'
 pipe=Pipeline([('preprocessing',prep),('model',est)]); Xtr,ytr=X.iloc[tr],y.iloc[tr]; Xte,yte=X.iloc[te],y.iloc[te]
 cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=42); t=time.time(); scores=cross_val_score(pipe,Xtr,ytr,cv=cv,scoring='f1_macro',n_jobs=1); cvtime=time.time()-t
 pd.DataFrame({'fold':np.arange(1,6),'macro_f1':scores}).to_csv(os.path.join(a.output_dir,prefix+'_5fold_cv_scores.csv'),index=False)
 summary={'model':name,'cv_method':'5-fold StratifiedKFold','cv_scope':'training set only','n_splits':5,'shuffle':True,'random_state':42,'scoring':'f1_macro','training_rows':len(tr),'held_out_test_rows_excluded_from_cv':len(te),'fold_macro_f1':[float(v) for v in scores],'mean_macro_f1':float(np.mean(scores)),'std_macro_f1':float(np.std(scores,ddof=1)),'cv_runtime_seconds':cvtime}
 json.dump(summary,open(os.path.join(a.output_dir,prefix+'_5fold_cv_summary.json'),'w'),indent=2)
 t=time.time(); pipe.fit(Xtr,ytr); trtime=time.time()-t; pred=pipe.predict(Xte); prob=pipe.predict_proba(Xte)[:,1]
 metrics={'model':name,'train_rows':len(tr),'test_rows':len(te),'train_indices_file':os.path.basename(a.train_indices),'test_indices_file':os.path.basename(a.test_indices),'accuracy':float(accuracy_score(yte,pred)),'macro_precision':float(precision_score(yte,pred,average='macro')),'macro_recall':float(recall_score(yte,pred,average='macro')),'macro_f1':float(f1_score(yte,pred,average='macro')),'roc_auc':float(roc_auc_score(yte,prob)),'confusion_matrix':confusion_matrix(yte,pred).tolist(),'training_runtime_seconds':trtime,'preprocessing':{'service_rating_zero_handling':'replace zero with missing and add *_not_applicable indicator','numeric_imputation':'median','categorical_imputation':'most_frequent','categorical_encoding':'OneHotEncoder(handle_unknown=ignore)','preprocessing_inside_pipeline':True},'cross_validation':'Separate CV files; CV uses X_train,y_train only; held-out test set excluded.'}
 json.dump(metrics,open(os.path.join(a.output_dir,prefix+'_metrics.json'),'w'),indent=2); pd.DataFrame({'row_index':te,'actual':yte.to_numpy(),'predicted':pred,'probability_satisfied':prob}).to_csv(os.path.join(a.output_dir,prefix+'_predictions.csv'),index=False); joblib.dump(pipe,os.path.join(a.output_dir,prefix+'_model.joblib'))
 print(json.dumps({'cv':summary,'test_metrics':metrics},indent=2))
if __name__=='__main__': main()
