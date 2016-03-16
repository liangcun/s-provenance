from pymongo import *
import exceptions
import traceback
from prov.model import ProvDocument, Namespace, Literal, PROV, Identifier
import datetime
import uuid
import traceback
import os
import socket
import json
import httplib, urllib
import csv
import StringIO
from urlparse import urlparse
from itertools import chain


def makeHashableList(listobj,field):
     listobj=[x[field] for x in listobj]
     return listobj

def clean_empty(d):
    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (clean_empty(v) for v in d) if v]
    return {k: v for k, v in ((k, clean_empty(v)) for k, v in d.items()) if v}

  
    

def toW3Cprov(ling,bundl,format='w3c-prov-xml'):
        
        g = ProvDocument()
        vc = Namespace("verce", "http://verce.eu")  # namespaces do not need to be explicitly added to a document
        con = Namespace("con", "http://verce.eu/control")
        g.add_namespace("dcterms", "http://purl.org/dc/terms/")
        
        'specify bundle'
        bundle=None
        for trace in bundl:
            'specifing user'
            ag=g.agent(vc[trace["username"]],other_attributes={"dcterms:author":trace["username"]})  # first time the ex namespace was used, it is added to the document automatically
            
            if trace['type']=='workflow_run':
                
                trace.update({'runId':trace['_id']})
                bundle=g.bundle(vc[trace["runId"]])
                bundle.actedOnBehalfOf(vc[trace["runId"]], vc[trace["username"]])
                
                dic={}
                i=0
                
                for key in trace:
                    
                
                    if key != "input": 
                        if ':' in key:
                            dic.update({key: trace[key]})
                        else:
                            dic.update({vc[key]: trace[key]})
                    
            
                dic.update({'prov:type': PROV['Bundle']})
                g.entity(vc[trace["runId"]], dic)
                
                dic={}
                i=0
                if type(trace['input'])!=list:
                    trace['input']=[trace['input']]
                for y in trace['input']:
                    for key in y:
                        if ':' in key:
                            dic.update({key: y[key]})
                        else:
                            dic.update({vc[key]: y[key]})
                    dic.update({'prov:type': 'worklfow_input'})
                    bundle.entity(vc[trace["_id"]+"_"+str(i)], dic)
                    bundle.used(vc[trace["_id"]], vc[trace["_id"]+"_"+str(i)], identifier=vc["used_"+trace["_id"]+"_"+str(i)])
                    i=i+1
                    
                    
        'specify lineage'
        for trace in ling:
            try:
                bundle=g.bundle(vc[trace["runId"]])
                bundle.wasAttributedTo(vc[trace["runId"]], vc["ag_"+trace["username"]],identifier=vc["attr_"+trace["runId"]])
            
            except:
                pass
            'specifing creator of the activity (to be collected from the registy)'
        
            if 'creator' in trace:
                bundle.agent(vc["ag_"+trace["creator"]],other_attributes={"dcterms:creator":trace["creator"]})  # first time the ex namespace was used, it is added to the document automatically
                bundle.wasAssociatedWith('process_'+trace["_id"],vc["ag_"+trace["creator"]])
                bundle.wasAttributedTo(vc[trace["runId"]], vc["ag_"+trace["creator"]])
    
            'adding activity information for lineage'
            dic={}
            for key in trace:
                
                if type(trace[key])!=list:
                    if ':' in key:
                        dic.update({key: trace[key]})
                    else:
                        
                        if key=='location':
                            
                            dic.update({"prov:location": trace[key]})    
                        else:
                            dic.update({vc[key]: trace[key]})
            bundle.activity(vc["process_"+trace["_id"]], trace["startTime"], trace["endTime"], dic.update({'prov:type': trace["name"]}))
        
            'adding parameters to the document as input entities'
            dic={}
            for x in trace["parameters"]:
                if ':' in x["key"]:
                    dic.update({x["key"]: x["val"]})
                else:
                    dic.update({vc[x["key"]]: x["val"]})
                
            dic.update({'prov:type':'parameters'})        
            bundle.entity(vc["parameters_"+trace["_id"]], dic)
            bundle.used(vc['process_'+trace["_id"]], vc["parameters_"+trace["_id"]], identifier=vc["used_"+trace["_id"]])

            'adding entities to the document as output metadata'
            for x in trace["streams"]:
                i=0
                parent_dic={}
                for key in x:
                        if key=='con:immediateAccess':
                            
                            parent_dic.update({vc['immediateAccess']: x[key]}) 
                            
                    
                        elif key=='location':
                             
                            parent_dic.update({"prov:location": str(x[key])})    
                        else:
                            parent_dic.update({vc[key]: str(x[key])})    
            
            
                c1=bundle.collection(vc[x["id"]],other_attributes=parent_dic)
                bundle.wasGeneratedBy(vc[x["id"]], vc["process_"+trace["_id"]], identifier=vc["wgb_"+x["id"]])
            
                for d in trace['derivationIds']:
                      bundle.wasDerivedFrom(vc[x["id"]], vc[d['DerivedFromDatasetID']],identifier=vc["wdf_"+x["id"]])
        
                for y in x["content"]:
                
                    dic={}
                
                    if isinstance(y, dict):
                        val=None
                        for key in y:
                        
                            try: 
                                val =num(y[key])
                                
                            except Exception,e:
                                val =str(y[key])
                            
                            if ':' in key:
                                dic.update({key: val})
                            else:
                                dic.update({vc[key]: val})
                    else:
                        dic={vc['text']:y}
                
                 
                    dic.update({"verce:parent_entity": vc["data_"+x["id"]]})
               
                    e1=bundle.entity(vc["data_"+x["id"]+"_"+str(i)], dic)
                
                    bundle.hadMember(c1, e1)
                    bundle.wasGeneratedBy(vc["data_"+x["id"]+"_"+str(i)], vc["process_"+trace["_id"]], identifier=vc["wgb_"+x["id"]+"_"+str(i)])
                
                    for d in trace['derivationIds']:
                        bundle.wasDerivedFrom(vc["data_"+x["id"]+"_"+str(i)], vc[d['DerivedFromDatasetID']],identifier=vc["wdf_"+"data_"+x["id"]+"_"+str(i)])
        
                    i=i+1
            
    
         
        
        if format =='w3c-prov-json':
            return str(g.serialize(format='json'))
        elif format=='png':
            output = StringIO.StringIO()
            g.plot('test.png')
            return output
            
        else:
            return g.serialize(format='xml')

class ProvenanceStore(object):

    def __init__(self, url):
 
        self.conection = MongoClient(host=url)
        self.db = self.conection["verce-prov"]
        self.lineage = self.db['lineage']
        self.workflow = self.db['workflow']
        
        'too specific here, have to be migrated to gateway-api'
        self.solver = self.db['solver']
        
    'extract information about a list of workflow runs starting from start to limit'    
    
#suport for rest call on workflow resources 
    def getWorkflows(self,**kwargs):
        
        try:
            keylist=None
            maxvaluelist=None
            minvaluelist=None
            if 'idlist' in kwargs:
                memory_file = StringIO.StringIO(kwargs['idlist'][0])
                idlist = csv.reader(memory_file).next()
                
                return self.getUserRunbyIds(kwargs['username'][0],idlist,**kwargs)
            else:
               try:
                    memory_file = StringIO.StringIO(kwargs['keys'][0]) if 'keys' in kwargs else None
                    keylist = csv.reader(memory_file).next() 
                    memory_file = StringIO.StringIO(kwargs['maxvalues'][0]); 
                    maxvaluelist = csv.reader(memory_file).next()
                    memory_file2 = StringIO.StringIO(kwargs['minvalues'][0]);
                    minvaluelist = csv.reader(memory_file2).next()
               except:
                    None;
                 #return {'success':False, 'error':'Invalid Query Parameters'}
               
               return self.getUserRunsValuesRange(kwargs['username'][0],keylist,maxvaluelist,minvaluelist,**kwargs)
  
        except Exception:
            traceback.print_exc()
            raise 
        #self.getUserRuns(kwargs['username'][0],**kwargs)
        
#suport for rest call on entities resources         
    def getEntities(self,**kwargs):
        keylist=None
        maxvaluelist=None
        minvaluelist=None
        vluelist=None
        try:
            memory_file = StringIO.StringIO(kwargs['keys'][0]) if 'keys' in kwargs else None
            keylist = csv.reader(memory_file).next()
            memory_file = StringIO.StringIO(kwargs['maxvalues'][0]);
            maxvaluelist = csv.reader(memory_file).next()
            memory_file = StringIO.StringIO(kwargs['minvalues'][0]);
            minvaluelist = csv.reader(memory_file).next()
            memory_file = StringIO.StringIO(request.args['values'][0]) if 'values' in kwargs else None
            vluelist = csv.reader(memory_file).next() if memory_file != None else None
            
            return self.getEntitiesBy(kwargs['method'][0],keylist,maxvaluelist,minvaluelist,vluelist,**kwargs)
  
        except Exception:
             
            traceback.print_exc()
            return self.getEntitiesBy(kwargs['method'][0],keylist,maxvaluelist,minvaluelist,vluelist,**kwargs)
            
        
    def makeElementsSearchDic(self,keylist,mnvaluelist,mxvaluelist):
        elementsDict={}
        
        for x in keylist:
            maxval=mxvaluelist.pop(0)
            minval=mnvaluelist.pop(0)
            try: 
                maxval =self.num(maxval)
                minval =self.num(minval)
            except Exception,e:
                None

                
            elementsDict.update({x:{"$lte":maxval,"$gte":minval }})
        
        searchDic={'streams.content':{'$elemMatch':elementsDict}}
        return searchDic
    
    def getEntitiesFilter(self,activ_searchDic,keylist,mxvaluelist,mnvaluelist,start,limit):
            elementsDict ={}
            searchDic={}
            #if iterationId!=None:
            
            if keylist==None:
                return self.lineage.find(activ_searchDic,{"runId":1,"streams":1,"parameters":1,'endTime':1,'errors':1})[start:start+limit].sort("endTime",direction=-1)
            else:
                
                for x in keylist:
                    
                    maxval=mxvaluelist.pop(0)
                    minval=mnvaluelist.pop(0)
                    try: 
                        maxval =self.num(maxval)
                        minval =self.num(minval)
                    except Exception,e:
                        None

                
                    elementsDict.update({x:{"$lte":maxval,"$gte":minval }})
                    searchDic={'streams.content':{'$elemMatch':elementsDict}}
                    
                    activ_searchDic.update(searchDic)
                    
                    
                 
                print "Filter Query: "+str(activ_searchDic)
                #obj =  self.lineage.find(activ_searchDic,{"runId":1,"streams.content.$":1,'endTime':1,'errors':1,"parameters":1})[start:start+limit].sort("endTime",direction=-1)
                obj= self.lineage.aggregate(pipeline=[{'$match':activ_searchDic},
                                                    {"$unwind": "$streams" },
                                                    #{ "$unwind": "$streams.content" },
                                                    {'$match':searchDic},
                                                    {'$group':{'_id':'$_id', 'parameters': { '$first': '$parameters' },'runId': { '$first': '$runId' },'endTime': { '$first': '$endTime' },'errors': { '$first': '$errors' },'streams':{ '$push':{'content' :'$streams.content','format':'$streams.format','location':'$streams.location','id':'$streams.id'}}}},
                                                    
                                                    ])['result'] 
                #print "DDD :"+json.dumps(obj)
                    
                return obj#totalCount=totalCount+self.lineage.find(activ_searchDic,{"runId":1}).count()
                    
            
            
            
            
            
            
    
    
    def exportRunProvenance(self, id,**kwargs):
        
        
        
        
        
        totalCount=self.lineage.find({'runId':id}).count()
        cursorsList=list()
        
        if 'all' in kwargs and kwargs['all'][0].upper()=='TRUE':
            
            lineage=self.lineage.find({'runId':id}).sort("endTime",direction=-1)
             
            bundle=self.workflow.find({"_id":id}).sort("startTime",direction=-1)
            
            if 'format' in kwargs:
                return toW3Cprov(lineage,bundle,format = kwargs['format'][0]),0
            else:
                return toW3Cprov(lineage,bundle),0
            
                    
                    
        output = {"w3c-prov":exportDocList};
        output.update({"totalCount": totalCount})
      
        return  (output,totalCount)
    
    def exportAllRunProvenance(self, id,**kwargs):
        
        
        
        
        
        totalCount=self.lineage.find({'runId':id}).count()+1
        cursorsList=list()
        
        if ('start' in kwargs and int(kwargs['start'][0])==0):
            cursorsList.append(self.workflow.find({"_id":id}))
        
        
        if 'all' in kwargs and kwargs['all'][0].upper()=='TRUE':
            
            cursorsList.append(self.lineage.find({'runId':id})[int(kwargs['start'][0]):int(kwargs['start'][0])+int(kwargs['limit'][0])].sort("endTime",direction=-1))
             
        else:
            cursorsList.append(self.lineage.find({'runId':id})[int(kwargs['start'][0]):int(kwargs['start'][0])+int(kwargs['limit'][0])].sort("endTime",direction=-1))

        exportDocList = list()
        
        
        
        
        
        for cursor in cursorsList:    
            for x in cursor:
                if 'format' not in kwargs or kwargs['format'][0].find('w3c-prov')!=-1:
                    
                    exportDocList.app(x,format = kwargs['format'][0] if 'format' in kwargs else 'w3c-prov-json')
        
        output = exportDocList
        
      
        return  (output,totalCount)
    
    def getSolverConf(self,path,request):
        try:
            solver = self.solver.find_one({"_id":path})
            if (solver!=None):
                solver.update({"success":True})
                userId = request.args["userId"][0] if "userId" in request.args else False
                def userFilter(item): return (not "users" in item) or (userId and userId in item["users"])
                def velmodFilter(item):
                    item["velmod"] = filter(userFilter, item["velmod"])
                    return item
                solver["meshes"] = map(velmodFilter, filter(userFilter, solver["meshes"]))
                return solver
            else:
                return {"success":False, "error":"Solver "+path+" not Found"}
            
        except Exception, e:
            return {"success":False, "error":str(e)}
    
    
    
    def getUserRunbyIds(self,userid,id_list,**kwargs):
        
         
        runids=[]
         
        obj=self.workflow.find({"_id":{"$in":id_list},'username':userid},{"startTime":-1,"system_id":1,"description":1,"name":1,"workflowName":1,"grid":1,"resourceType":1,"resource":1,"queue":1}).sort("startTime",direction=-1)
        totalCount=self.workflow.find({"_id":{"$in":id_list}}).sort("startTime",direction=-1).count()
        for x in obj:
            
            runids.append(x)
        
            
        output = {"runIds":runids};
        output.update({"totalCount": totalCount})
        
        return output
    
    
    def getUserRunsValuesRange(self,userid,keylist,maxvaluelist,minvaluelist,**kwargs):
        elementsDict ={}
        output=None
        runids=[]
        uniques=None
        totalCount=0
        start=int(kwargs['start'][0])
        limit=int(kwargs['limit'][0])
        if keylist==None: 
            keylist=[]
        
        if ((keylist==None or len(keylist)==0) and 'activities' not in kwargs):
            return self.getUserRuns(userid, **kwargs)
        
        if 'activities' in kwargs:
            #print str(kwargs)
            values=str(kwargs['activities'][0]).split(',')
            intersect=False
            for y in values:
                #totalCount=totalCount+len(self.lineage.find({'username':userid,'name':y}).distinct("runId"))
                uniques_act=self.lineage.aggregate(pipeline=[{'$match':{'username':userid,'name':y}},
                                                    {'$group':{'_id':'$runId','startTime':{ '$first': '$startTime' }}},
                                                    {'$sort':{'startTime':-1}},
                                                    {'$project':{'_id':1}}
                                                    ])['result'] 
                
                uniques_act=makeHashableList(uniques_act,'_id')
                if intersect==True:
                    uniques=list(set(uniques).intersection(set(uniques_act)))
                else:
                    uniques=uniques_act
                    intersect=True
                
         
        
        if len(keylist)!=0 and "mime-type" in keylist:
            values=list((set(minvaluelist).union(set(maxvaluelist))))
            #totalCount=totalCount+len(self.lineage.find({'username':userid,'streams.format':{'$in':values}}).distinct("runId"))
            uniques_mime=self.lineage.aggregate(pipeline=[{'$match':{'username':userid,'streams.format':{'$in':values}}},
                                                    {'$group':{'_id':'$runId','startTime':{ '$first': '$startTime' }}},
                                                    {'$sort':{'startTime':-1}},
                                                    {'$project':{'_id':1}}
                                                    ])['result'] 
            
            #self.lineage.find({'username':userid,'streams.format':{'$in':values}}).distinct("runId")
            uniques_mime=makeHashableList(uniques_mime,'_id')

            i = keylist.index('mime-type')
            minvaluelist.pop(i)
            maxvaluelist.pop(i)
            keylist.remove('mime-type')
            
            if uniques!=None:
                uniques=list(set(uniques).intersection(set(uniques_mime)))
            else:
                uniques=uniques_mime
        
        
        for x in keylist:
            maxval=maxvaluelist.pop(0)
            minval=minvaluelist.pop(0)
            try: 
                maxval =self.num(maxval)
                minval =self.num(minval)
            except Exception,e:
                None
            
            objdata=self.lineage.aggregate(pipeline=[{'$match':{'username':userid,'streams.content':{'$elemMatch':{x:{"$lte":maxval,"$gte":minval }}}}},
                                                    {'$group':{'_id':'$runId','startTime':{ '$first': '$startTime' }}},
                                                    {'$sort':{'startTime':-1}},
                                                    {'$project':{'_id':1}}
                                                    ])['result'] 
            objdata=makeHashableList(objdata,'_id')
            #self.lineage.find({'username':userid,'streams.content':{'$elemMatch':{x:{"$lte":maxval,"$gte":minval }}}},{"startTime":-1,'runId':1}).sort("startTime",direction=-1).distinct("runId") 
            objpar=self.lineage.aggregate(pipeline=[{'$match':{'username':userid,'parameters':{'$elemMatch':{'key':x,'val':{"$lte":maxval,"$gte":minval }}}}},
                                                    {'$group':{'_id':'$runId','startTime':{ '$first': '$startTime' }}},
                                                    {'$sort':{'startTime':-1}},
                                                    {'$project':{'_id':1}}
                                                    ])['result']
            objpar=makeHashableList(objpar,'_id')
            #self.lineage.find({'username':userid,'parameters':{'$elemMatch':{'key':x,'val':{"$lte":maxval,"$gte":minval }}}},{"startTime":-1,'runId':1}).sort("startTime",direction=-1).distinct("runId")           
              
            object_union=list(set(objdata).union(set(objpar)))
            
             
            
            if uniques!=None:
                 
                uniques=list(set(uniques).intersection(set(object_union)))
                 
            else:
                uniques=object_union
                
      
       
        totalCount=len(uniques)
        
        #uniques=[x['_id'] for x in uniques]
        
        obj=self.workflow.find({"_id":{"$in":uniques[start:start+limit]}},{"startTime":-1,"system_id":1,"description":1,"name":1,"workflowName":1,"grid":1,"resourceType":1,"resource":1,"queue":1}).sort("startTime",direction=-1)
         
        for x in obj:
            
            runids.append(x)
        
            
        output = {"runIds":runids};
        output.update({"totalCount": totalCount})
        
        return output
    
    
    def getEntitiesByValuesRange(self,path,keylist,mtype,start,limit,runId=None,iterationId=None,dataId=None,maxvaluelist=None,minvaluelist=None,valuelist=None):
         
        elementsDict ={}
        output=None
        runids=[]
        uniques=None
       
        for x in keylist:
            maxval=maxvaluelist.pop(0)
            minval=minvaluelist.pop(0)
            try: 
                maxval =self.num(maxval)
                minval =self.num(minval)
            except Exception,e:
                None
             
            if runId!=None:
                
                objdata=self.lineage.find({'runId':runId,'streams.format':mtype,'streams.content':{'$elemMatch':{x:{"$lte":maxval,"$gte":minval }}}},{"runId":1,"streams.content.$":1,'streams':1,'endTime':1,'errors':1,"parameters":1}) 
                objpar=self.lineage.find({'runId':runId,'streams.format':mtype,'parameters':{'$elemMatch':{'key':x,'val':{"$lte":maxval,"$gte":minval }}}},{"runId":1,"streams.content.$":1,'streams':1,'endTime':1,'errors':1,"parameters":1}) 
                
                object_union=list(set(objdata).union(set(objpar)))
                
                
            else:
                
                objdata=self.lineage.find({'streams.format':mtype,'streams.content':{'$elemMatch':{x:{"$lte":maxval,"$gte":minval }}}},{"runId":1,"streams.content.$":1,'streams':1,'endTime':1,'errors':1,"parameters":1}) 
                objpar=self.lineage.find({'streams.format':mtype,'parameters':{'$elemMatch':{'key':x,'val':{"$lte":maxval,"$gte":minval }}}},{"runId":1,"streams.content.$":1,'streams':1,'endTime':1,'errors':1,"parameters":1})            
                object_union=list(set(objdata).union(set(objpar)))
                
            if (uniques!=None):
                uniques=list(set(uniques).intersection(set(object_union)))
                
            else:
           
                uniques=object_union
                
        
        totalCount=len(uniques)
          
        
               
        
        
                    
        artifacts = list()

        
        for x in  uniques:
            
            for s in x["streams"]:
                totalCount=totalCount+1
                s["wasGeneratedBy"]=x["_id"]
                s["parameters"]=x["parameters"]
                s["endTime"]=x["endTime"]
                s["runId"]=x["runId"]
                s["errors"]=x["errors"]
                artifacts.append(s)
                    
        
                
        output = {"entities":artifacts};
        output.update({"totalCount": totalCount})
        return  output
        
        
    
    def getRunInfo(self, path):
        
         obj = self.workflow.find_one({"_id":path})
         return obj

         
     
    def getUserRuns(self, path, **kwargs):
        
        
        obj=None
        totalCount=None
        output=None
        start=int(kwargs['start'][0])
        limit=int(kwargs['limit'][0])
        
        
        if 'activities' in kwargs:
            return self.getUserRunsValuesRange(kwargs['username'][0],None,None,None,**kwargs)
        else:
            obj = self.workflow.find({"username":path},{"_id":-1,"startTime":-1,"system_id":1,"description":1,"name":1,"workflowName":1,"grid":1,"resourceType":1,"resource":1,"queue":1}).sort("startTime",direction=-1)[start:start+limit]

        totalCount=self.workflow.find({"username":path}).count()
        runids = list()
        
        for x in obj:
                
            runids.append(x)
            
        output = {"runIds":runids};
        output.update({"totalCount": totalCount})
    
        return  output
    
    
    def num(self,s):
        try:
            return int(s)
        except exceptions.ValueError:
            return float(s)

     
    
    
    def getEntitiesBy(self,meth,keylist,mxvaluelist,mnvaluelist,vluelist,**kwargs):
        totalCount=0;
        cursorsList=list()
        obj=None
        
        start=int(kwargs['start'][0]) if 'start' in kwargs and kwargs['start'][0]!='null' else None
        limit=int(kwargs['limit'][0]) if 'limit' in kwargs and kwargs['limit'][0]!='null' else None
        runId=kwargs['runId'][0].strip() if 'runId' in kwargs and kwargs['runId'][0]!='null' else None
        dataId=kwargs['dataId'][0].strip() if 'dataId' in kwargs and kwargs['dataId'][0]!='null' else None
        iterationId=kwargs['iterationId'][0].strip() if 'iterationId' in kwargs and kwargs['iterationId'][0]!='null' else None
        mtype=kwargs['mime-type'][0].strip() if 'mime-type' in kwargs and kwargs['mime-type'][0]!='null' else None
        activities=None
        
        if 'activities' in kwargs:
            activities=str(kwargs['activities'][0]).split(',')
            
        i=0
        ' extract data by annotations either from the whole archive or for a specific runId'
         
        activ_searchDic={'_id':iterationId,'name':{'$in':activities},'runId':runId,'streams.format':mtype}
        activ_searchDic=clean_empty(activ_searchDic)
        #print activ_searchDic
    
        
        
        if meth=="annotations":
            if runId!=None:
                for x in keylist:
                    cursorsList.append(self.lineage.find({'streams.annotations':{'$elemMatch':{'key': x,'val':{'$in':vluelist}}},'runId':runId},{"runId":1,"streams.annotations.$":1,'streams':1,'endTime':1,'errors':1,"parameters":1,})[start:start+limit].sort("endTime",direction=-1))
                    totalCount = totalCount + self.lineage.find({'streams.annotations':{'$elemMatch':{'key': x,'val':{'$in':vluelist}}},'runId':runId},).count()
            else:
                for x in keylist:
                    cursorsList.append(self.lineage.find({'streams.annotations':{'$elemMatch':{'key': x,'val':{'$in':vluelist}}}},{"runId":1,"streams.annotations.$":1,'streams':1,'endTime':1,'errors':1,"parameters":1})[start:start+limit].sort("endTime",direction=-1))
                    totalCount = totalCount + self.lineage.find({'streams.annotations':{'$elemMatch':{'key': x,'val':{'$in':vluelist}}}},).count()
        
        if meth=="generatedby":
            cursorsList.append(self.getEntitiesFilter(activ_searchDic,keylist,mxvaluelist,mnvaluelist,start,limit))
        elif meth=="run":        
            cursorsList.append(self.lineage.find({'runId':runId,'streams.id':dataId},{"runId":1,"streams":{"$elemMatch": { "id": dataId}},"parameters":1,'endTime':1,'errors':1}))
            totalCount = totalCount + self.lineage.find({'runId':runId,'streams.id':dataId}).count()
        elif meth=="values-range":
            cursorsList.append(self.getEntitiesFilter(activ_searchDic,keylist,mxvaluelist,mnvaluelist,start,limit))
        
        else:
            cursorsList.append(self.lineage.find({'streams.id':meth},{"runId":1,"streams":{"$elemMatch": { "id": meth}},"parameters":1,'endTime':1,'errors':1}))
                
            
        artifacts = list()

        for cursor in cursorsList:
            for x in cursor:
                
                for s in x["streams"]:
                     
                    if (mtype==None or mtype=="") or ('format' in s and s["format"]==mtype):
                        totalCount=totalCount+1
                        s["wasGeneratedBy"]=x["_id"]
                        s["parameters"]=x["parameters"]
                        s["endTime"]=x["endTime"]
                        s["runId"]=x["runId"]
                        s["errors"]=x["errors"]
                        artifacts.append(s)
                    
        
                
        output = {"entities":artifacts};
        output.update({"totalCount": totalCount})
       
        return  output
         
    def getActivities(self, id,start,limit):
        obj = self.lineage.find({'runId':id},{"runId":1,"instanceId":1,"parameters":1,"endTime":-1,"errors":1,"iterationIndex":1,"iterationId":1,"streams.con:immediateAccess":1,"streams.location":1})[start:start+limit].sort("endTime",direction=-1)
        totalCount=self.lineage.find({'runId':id},{"instanceId":1}).count()
        activities = list()
        
        for x in obj:
            activities.append(x)
            
        output = {"activities":activities};
        output.update({"totalCount": totalCount})
        return  output
    
    def editRun(self, id,doc):
        ret=[]
        response={}
        
        try:
            
            self.workflow.update({"_id":id},{'$set':doc})
        
            response={"success":True}
            response.update({"edit":id}) 
        
        except Exception, err:
            response={"success":False}
            response.update({"error":str(err)})
            traceback.print_exc()
        finally:
            return response
        
        
    def deleteRun(self, id):
        ret=[]
        response={}
        
        try:
            if (self.workflow.find_one({"_id":id})!=None):
                self.lineage.remove({"runId":id})
                self.workflow.remove({"_id":id})
            
                response={"success":True}
                response.update({"delete":id}) 
            else:
                response={"success":False}
                response.update({"error":"Workflow run "+id+" does not exist!"}) 
            
        except Exception, err:
            response={"success":False}
            response.update({"error":str(err)})
            traceback.print_exc()
        finally:
            return response
    
    def insertWorkflow(self, json):
        ret=[]
        response={}
        
        try:
            if type(json) =='list':
        
                for x in json:
                    
                    ret.append(self.workflow.insert(x))
            else:
                ret.append(self.workflow.insert(json))
        
            response={"success":True}
            response.update({"inserts":ret}) 
        
        except Exception, err:
            response={"success":False}
            response.update({"error":str(err)}) 
        finally:
            return response
    
    
    ' insert new data in different collections depending from the document type'

    def updateCollections(self, prov):
        try:
            if prov["type"]=="lineage":
                if prov["type"]=="lineage":
                    return self.lineage.insert(prov)
                # if(self.workflow.find_one({"_id":prov["runId"]})!=None):
                #     return self.lineage.insert(prov)
                # else: 
                #     raise Exception("Workflow Run not found")

            if prov["type"]=="workflow_run":
             
                return self.workflow.insert(prov)
        
        except Exception, err:
            raise
            
    def insertData(self, prov):
        ret=[]
        response={}
        
        
        try:
            if type(prov).__name__ =='list':
                 
                for x in prov:
                   try:
                       ret.append(self.updateCollections(x))
                   except Exception, err:
                       ret.append({"error":str(err)})
            else:
                try:
                 
                    ret.append(self.updateCollections(prov))
                except Exception, err:
                       ret.append({"error":str(err)})
        
            response={"success":True}
            response.update({"inserts":ret}) 
        
        except Exception, err:
            
            response={"success":False}
            response.update({"error":str(err)}) 
            
        finally:
            return response
    
    
    def getDerivedDataTrace(self, id,level):
         
        xx = self.lineage.find_one({"streams.id":id},{"runId":1});
        xx.update({"dataId":id})
        cursor=self.lineage.find({"derivationIds":{'$elemMatch':{"DerivedFromDatasetID":id}}},{"runId":1,"streams":1});
         
        
        if level>0:
            derivedData=[]
            
            i=0
            for d in cursor:
                i+=1
                if (i<25):
                 
                 
                 
                    for str in d["streams"]:
                     
                        try:
                            derivedData.append(self.getDerivedDataTrace(str["id"],level-1))
                        
                        except Exception, err:
                            None
                 
                 
                
            xx.update({"derivedData":derivedData})
                
            
         
        
      
        return xx
        
    def getTrace(self, id,level):
         
        xx = self.lineage.find_one({"streams.id":id},{"runId":1,"derivationIds":1});
         
         
        xx.update({"id":id})
        if level>=0:
            for derid in xx["derivationIds"]:
                try:
                    derid["wasDerivedFrom"] = self.getTrace(derid["DerivedFromDatasetID"],level-1)
                except Exception, err:
                    None
            return xx
        
    
    
    def filterOnAncestorsValuesRange(self,idlist,keylist,minvaluelist,maxvaluelist):
        filteredIds=[]
        for x in idlist:
            test=self.hasAncestorWithValuesRange(x,keylist,minvaluelist,maxvaluelist)
         #   print test
            if test["hasAncestorWith"]==True:
                filteredIds.append(x)
        
        return filteredIds
    
    def filterOnAncestorsMeta(self,idlist,keylist,valuelist):
        filteredIds=[]
        for x in idlist:
            test=self.hasAncestorWith(x,keylist,valuelist)
         #   print test
            if test["hasAncestorWith"]==True:
                filteredIds.append(x)
        
        return filteredIds
    
    def filterOnMeta(self,idlist,keylist,valuelist):
        filteredIds=[]
        for x in idlist:
            test=self.hasMeta(x,keylist,valuelist)
        #   print test
            if test["hasMeta"]==True:
                filteredIds.append(x)
        
        return filteredIds
            
    
    def hasMeta(self, id, keylist,valuelist):
         
        elementsDict ={}
        
        k=0
        for x in keylist:
            val=valuelist[k]
            k+=1
            try: 
                val =self.num(val)
            except Exception,e:
                None

            elementsDict.update({x:val})
        
        xx = self.lineage.find_one({"streams":{"$elemMatch":{"id":id,'content':{'$elemMatch':elementsDict}}}},{"streams.id":1});
        if (xx!=None):    
            
            return {"hasMeta":True}
                    
                  
        else:
            return {"hasMeta":False}
    
                
    def hasAncestorWithValuesRange(self, id, keylist,minvaluelist,maxvaluelist):
         
        elementsDict ={}
        k=0
        for x in keylist:
            maxval=maxvaluelist[k]
            minval=minvaluelist[k]
            k+=1
            try: 
                maxval =self.num(maxval)
                minval =self.num(minval)
            except Exception,e:
                None
                

            elementsDict.update({x:{"$lte":maxval,"$gte":minval }})
        
        xx = self.lineage.find_one({"streams.id":id},{"runId":1,"derivationIds":1});
        if len(xx["derivationIds"])>0:    
            for derid in xx["derivationIds"]:
                try:
                #    print derid["DerivedFromDatasetID"]
                    anchestor = self.lineage.find_one({"streams":{"$elemMatch":{"id":derid["DerivedFromDatasetID"],'content':{'$elemMatch':elementsDict}}}},{"streams.id":1});
                    
                    if anchestor!=None:
                        return {"hasAncestorWith":True}
                    else:
                        return self.hasAncestorWithValuesRange(derid["DerivedFromDatasetID"],keylist,minvaluelist,maxvaluelist)
                except Exception,e: 
                   traceback.print_exc()
        else:
            return {"hasAncestorWith":False}
        
    
    def hasAncestorWith(self, id, keylist,valuelist):
         
        elementsDict ={}
        
        k=0
        for x in keylist:
            val=valuelist[k]
            k+=1
            try: 
                val =self.num(val)
            except Exception,e:
                None

            elementsDict.update({x:val})
        
        xx = self.lineage.find_one({"streams.id":id},{"runId":1,"derivationIds":1});
        if len(xx["derivationIds"])>0:    
            for derid in xx["derivationIds"]:
                try:
                #    print derid["DerivedFromDatasetID"]
                    anchestor = self.lineage.find_one({"streams":{"$elemMatch":{"id":derid["DerivedFromDatasetID"],'content':{'$elemMatch':elementsDict}}}},{"streams.id":1});
                    
                    if anchestor!=None:
                        return {"hasAncestorWith":True}
                    else:
                        return self.hasAncestorWith(derid["DerivedFromDatasetID"],keylist,valuelist)
                except Exception,e: 
                   traceback.print_exc()
        else:
            return {"hasAncestorWith":False}
       
        
        
    def getTraceConditonalX(self, id, keylist,valuelist):
         
        elementsDict ={}
        
        k=0
        for x in keylist:
            val=valuelist[k]
            k+=1
            try: 
                val =self.num(val)
            except Exception,e:
                None

            elementsDict.update({x:val})
        
        xx = self.lineage.find_one({"streams.id":id,'streams.content':{'$elemMatch':elementsDict}},{"runId":1,"derivationIds":1});
        
        if xx==None:
            xx = self.lineage.find_one({"streams.id":id},{"runId":1,"derivationIds":1});
             
            xx.update({"id":id})
            
            for derid in xx["derivationIds"]:
                try:
                    val = self.getTraceConditonal(derid["DerivedFromDatasetID"],keylist,valuelist)
                     
                    if val!=None:
                        return {"hasAnchestor":True}
                    
                except Exception, err:
                    traceback.print_exc()
            
        else:
            return xx
        
        
    def getActivitiesSummaries(self,**kwargs): 
        obj=[]
        runId=None
        groupby=kwargs['groupby'][0]
        print groupby
        if 'runId' in kwargs : runId = kwargs['runId'][0]
        
        if 'level' in kwargs and kwargs['level'][0]=='prospective':
            obj=self.lineage.aggregate(pipeline=[{'$match':{'runId':runId}},{'$unwind': "$streams"},{'$group':{'_id':{'actedOnBehalfOf':'$actedOnBehalfOf','name':'$name', str(groupby):'$'+str(groupby) }, 'time':{'$min': '$startTime'}}},{'$sort':{'time':1}}])['result']
        elif 'level' in kwargs and kwargs['level'][0]=='iterations':
            obj=self.lineage.aggregate(pipeline=[{'$match':{'runId':runId,'iterationIndex':{'$gte':int(kwargs['minidx'][0]) ,'$lt':int(kwargs['maxidx'][0])}}},{'$unwind': "$streams"},{'$group':{'_id':{'iterationId':'$iterationId','instanceId':'$instanceId','worker':'$worker',str(groupby):'$'+str(groupby)}, 'time':{'$min': '$startTime'}}},{'$sort':{'time':1}}])['result']
        elif 'level' in kwargs and kwargs['level'][0]=='instances':
            obj=self.lineage.aggregate(pipeline=[{'$match':{'runId':runId}},{'$unwind': "$streams"},{'$group':{'_id':{'instanceId':'$instanceId','actedOnBehalfOf':'$actedOnBehalfOf','worker':'$worker',str(groupby):'$'+str(groupby)}, 'time':{'$min': '$startTime'}}},{'$sort':{'time':1}}])['result']
        elif 'level' in kwargs and kwargs['level'][0]=='pid':
            obj=self.lineage.aggregate(pipeline=[{'$match':{'runId':runId}},{'$group':{'_id':{'name':'$name','worker':'$worker','pid':'$pid'}}}])['result']
        elif 'level' in kwargs and kwargs['level'][0]=='workers':
            obj=self.lineage.aggregate(pipeline=[{'$match':{'runId':runId}},{'$group':{'_id':{'name':'$name','worker':'$worker'}}}])['result']
       # elif 'level' in kwargs and kwargs['level'][0]=='terms':
       #      obj=self.lineage.aggregate(pipeline=[{'$match':{'runId':runId}},{'$group':{'_id':{'instanceId':'$instanceId'}}}])['result']
        elif 'level' in kwargs and kwargs['level'][0]=='vrange':
            memory_file = StringIO.StringIO(kwargs['keys'][0]);
            keylist = csv.reader(memory_file).next()
            memory_file = StringIO.StringIO(kwargs['maxvalues'][0]);
            mxvaluelist = csv.reader(memory_file).next()
            memory_file = StringIO.StringIO(kwargs['minvalues'][0]);
            mnvaluelist = csv.reader(memory_file).next()
            memory_file = StringIO.StringIO(kwargs['users'][0]);
            users = csv.reader(memory_file).next()
            searchDic = self.makeElementsSearchDic(keylist,mnvaluelist,mxvaluelist)
            
            for y in searchDic['streams.content']['$elemMatch']:
                #print " searchdic "+json.dumps(searchDic['streams.content']['$elemMatch'][y])+"\n"
                obj = obj + self.lineage.aggregate(pipeline=[{'$match':{'username':{'$in':users},'streams.content':{'$elemMatch':{y:searchDic['streams.content']['$elemMatch'][y]}}}},
                                                    {'$group':{'_id': '$runId'}},
                                                    ])['result']
                
        else:
            obj=self.lineage.aggregate(pipeline=[{'$match':{'runId':runId}},{'$group':{'_id':{'name':'$name'}}},{'$project':{'_id':1}}])['result']
       
        print "OBJ: "+str(obj)
        connections=[]
        
       
        for x in obj:
            add=True
            if runId:
                x['_id'].update({'runId':runId})
            
            triggers=None
            if 'level' in kwargs and kwargs['level'][0]=='vrange':
                try:
                    
                    triggers=self.workflow.aggregate(pipeline=[{'$match':{'_id':x['_id']}},{'$unwind':'$input'},{'$match':{'$or':[{'input.prov:type':'wfrun'},{'input.prov-type':'wfrun'}]}},{'$project':{'input.url':1,'_id':0}}])['result']
                    #print 'TRIG '+x['_id']+' '+ json.dumps(triggers)
                except:
                    traceback.print_exc()
                    triggers=[]
                
                    #print "wf ID "+str(x['_id'])
                try:
                    wfitem=self.workflow.find({'_id':x['_id']},{'workflowName':1})[0]
                    x['_id']=wfitem['workflowName']+'.'+x['_id'] 
                        #print "wfname"+str(wfitem['workflowName'])
                except:
                    #print "wf ID "+str(x['_id'])+" not found inf workflow collection"
                    add=not add
                     
                     
                         
            elif 'level' in kwargs and kwargs['level'][0]=='pid':
                triggers=self.lineage.aggregate(pipeline=[{'$match':x['_id']},{'$unwind':'$derivationIds'},{'$group':{'_id':'$derivationIds.TriggeredByProcessIterationID'}}])['result']
            elif 'level' in kwargs and (kwargs['level'][0]=='instances' or kwargs['level'][0]=='iterations' or kwargs['level'][0]=='prospective'):
                triggers=self.lineage.aggregate(pipeline=[{'$match':x['_id']},{'$sort':{'startTime':1}},{'$unwind':'$derivationIds'},{'$group':{'_id':'$derivationIds.TriggeredByProcessIterationID'}}])['result']
            elif 'level' in kwargs and kwargs['level'][0]=='workers':
                triggers=self.lineage.aggregate(pipeline=[{'$match':x['_id']},{'$unwind':'$derivationIds'},{'$group':{'_id':'$derivationIds.TriggeredByProcessIterationID'}}])['result']
           
            else:
                triggers=self.lineage.aggregate(pipeline=[{'$match':{'runId':runId,'name':x['_id']}},{'$unwind':'$derivationIds'},{'$group':{'_id':'$derivationIds.TriggeredByProcessIterationID'}}])['result']
            
            
            for t in triggers:
                t['iterationId']=t['_id']
                del t['_id']
                
                
            #print "triggers "+str(x['_id'])+" "+json.dumps(triggers)+" "+str(add)
            if add and len(triggers)>0:
                pes=[]
                
                if 'level' in kwargs and kwargs['level'][0]=='prospective':
                    pes=self.lineage.aggregate(pipeline=[{'$match':{'$or':triggers}},{'$sort':{'startTime':1}},{'$unwind':'$streams'},{'$group':{'_id':{'actedOnBehalfOf':'$actedOnBehalfOf','rundId':'$runId','name':'$name'},'size':{'$sum':'$streams.size'}}}])['result']
                elif 'level' in kwargs and kwargs['level'][0]=='pid':
                    pes=self.lineage.aggregate(pipeline=[{'$match':{'$or':triggers}},{'$project':{'name':1,'worker':1,'_id':0,'pid':1}}])['result']
                elif 'level' in kwargs and kwargs['level'][0]=='iterations':
                    pes=self.lineage.aggregate(pipeline=[{'$match':{'$or':triggers}},{'$sort':{'startTime':1}},{'$unwind':'$streams'},{'$group':{'_id':{'instanceId':'$instanceId','worker':'$worker','iterationId':'$iterationId'},'size':{'$sum':'$streams.size'}}}])['result']
                elif 'level' in kwargs and kwargs['level'][0]=='instances':
                    pes=self.lineage.aggregate(pipeline=[{'$match':{'$or':triggers}},{'$sort':{'startTime':1}},{'$unwind':'$streams'},{'$group':{'_id':{'instanceId':'$instanceId','worker':'$worker','actedOnBehalfOf':'$actedOnBehalfOf'},'size':{'$sum':'$streams.size'}}}])['result']
                elif 'level' in kwargs and kwargs['level'][0]=='workers':
                    pes=self.lineage.aggregate(pipeline=[{'$match':{'$or':triggers}},{'$project':{'name':1,'worker':1,'_id':0}}])['result']
                elif 'level' in kwargs and kwargs['level'][0]=='vrange':
                    for w in triggers:
                        up=urlparse(w['input']['url']).path
                        up=up[up.rfind('/')+1:len(up)+1]
                        #print up
                        curs=self.workflow.find({'_id':up})
                        if (curs.count()>0):
                            pes.append(curs[0]['workflowName']+'.'+up)
                else:
                    pes=self.lineage.aggregate(pipeline=[{'$match':{'$or':triggers}},{'$project':{'name':1,"_id":0}}])['result']
                
                x.update({'name':x['_id'], 'connlist':pes})
                #print "conections done for: "+str(x['_id'])
                
                del x['_id']
                connections.append(x)
                
                 
                
            elif add:
                x.update({'name':x['_id'], 'connlist':[]})
                del x['_id']
                connections.append(x)
                
        #print "PES: "+str(connections)
        return connections