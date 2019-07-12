#!/usr/bin/env python
from flask_restful import Resource, Api
import requests
import base64
import json
from flask import Flask, request, jsonify
import sys
import json, ast, base64, yaml, re
import os
import time
import json
import shutil
from flask import Flask, jsonify, request
from ansible.module_utils.common.collections import ImmutableDict
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
from ansible import context
import ansible.constants as C
import sys, os, base64, datetime, hashlib, hmac
from flask_restful import Resource, Api
import xmltodict

app = Flask(__name__)
api = Api(app)


class EXT_CRED(Resource):
    def post(self):

			payload = json.loads(request.data)

			print 'payload for execution using ansible -> ',

			print payload
                        print format(str(payload))

			opr_stat_template = base64.decodestring(payload['template'])    #payload['template']

			operationtemplate = (json.loads(opr_stat_template)['execPlay'])
			statustemplate = (json.loads(opr_stat_template)['status'])

#--------------------------------------------extracting credentials--------------------------------------
			try:
				d=request.headers #accepting input in json format

        	                acc_id = d['cb-user-provider-account'] #storing account id in a var
                	        cred_id = d['cb-provider-credential-refid'] #storing credential id in a var
			except:
				print
				print 'NO HEADER FILE SUPPLIED CONTAINING ACCOUNT-ID AND CREDENTIAL-ID'
				print
				sys.exit()

                        api_key = '97ea0f84-d73f-5533-954f-22a4d98ae619' #hardcoding apikey and username
                        username = 'bavanapa'

                        head = {'Apikey':api_key, 'Username':username}
                        request_url = 'https://partner-dev2-api.gravitant.net/cb-credential-service/api/v2.0/accounts/'+acc_id+'/credentials?credentialId='+cred_id
			#final url to be called


			response = requests.get(request_url, headers=head)
			#storing response of the url in a var
			if str(response.status_code)[0]=='4':
				print
				print 'INVALID CREDENTIALS i.e. ANY OF (APIKEY, USERNAME, ACCOUNT_ID, CREDENTIAL_ID)'
				print
				sys.exit()

			if str(response.status_code)[0]=='5':
                                print
                                print 'AWS SERVER ERROR, TRY AGAIN LATER'
                                print
                                sys.exit()


			dic = {} #creating a dictionary to store access key and secret key
			vars = {}

#--------------------------------------------------loading varibles from the var section in the playbook---------------
			play = yaml.safe_load(base64.decodestring(str(operationtemplate)).encode('ascii'))
                        json_file = json.dumps(play)
                        playbook_py = json.loads(json_file)

			child_dic = playbook_py[0]['vars']
			for i in child_dic.keys():
				vars[i] = child_dic[i]

			region, instance_id = str(payload['resourceInfo']['id']).split('~')

			vars['region'] = region
			vars['instance_id'] = instance_id

#-----------------------------------------------------------------------------------------------------------------------
			vars['Apikey'] = '97ea0f84-d73f-5533-954f-22a4d98ae619'
			vars['Username'] = 'bavanapa'
			vars['acc_id'] = acc_id
			vars['cred_id'] = cred_id

			template = {}
			template['operationtemplate'] = operationtemplate
			template['statustemplate'] = statustemplate

			dic['aws_access_key'] = (json.loads(str(response.content)))['credentials'][0]['passwordFields']['accessKey']
			dic['aws_secret_key'] = (json.loads(str(response.content)))['credentials'][0]['passwordFields']['secretKey']
			dic['template'] = template
			dic['vars'] = vars

			execplayheader = {'template': operationtemplate }
			statplayheader = {'template': statustemplate }
#-----------------------------------------------------calling api to execute operation template-------------------------------------

			operationplay = requests.post(url='http://localhost:5000/aws/ansible/executePlay', headers=execplayheader, data=json.dumps(dic))


			if str(operationplay.status_code)[0]=='4' or str(operationplay.status_code)[0]=='5':
				print
				print '------------------------SYNTAX ERROR------------------------'
				print 'INCORRECT ANSIBLE OPERATION PLAYBOOK INPUT, KINDLY TRY AGAIN'
				sys.exit()

			print
			print 'operation play output - ',
			print operationplay.content
			print


#---------------------------------------data for posting execution template ----------------------------------
                        execurl = 'https://partner-dev2-api.gravitant.net:443/message/OperationFulfillment'
                        execheader = {
                                         "Content-Type": "application/json",
                                         "Accept": "application/json",
                                         "Username":"bavanapa",
                                         "Apikey":"97ea0f84-d73f-5533-954f-22a4d98ae619"
                                     }
                        execbody = {
                                    "routingKey": "operation_fulfillment_response",
                                    "messageContent": {
                                                              "teamId": payload['teamId'],
                                                              "orderNumber": payload['orderNumber'],
                                                              "operationNumber": payload['operationRequestId'],
                                                              "version": "v1",
                                                              "operationTrackingInfo": {
                                                                                                "statusTemplate": statustemplate,
												"vars":dic['vars'],
                                                                                       }
                                                      }
	                                   }

			if dic['vars']['action'] == 'StartInstances' or dic['vars']['action'] == 'StopInstances':
				execbody["messageContent"]["operationTrackingInfo"]["current_state"] = json.loads(operationplay.content)['current_state']
				execbody["messageContent"]["operationTrackingInfo"]["previous_state"] = json.loads(operationplay.content)['previous_state']


			print '----------------------------------      EXEC QUEUE -----------------------'
                        print (execbody)
                        print '-----------------------------------------------------------------------------'
                        print format(str(execbody))


			postoprtemplate = requests.post(execurl, headers=execheader, data=json.dumps(execbody))
                        print 'post operation template api returned code - ',
               	        print postoprtemplate.content

			return jsonify(json.loads(operationplay.content)) #returning dictionary containing access key and secret key

class POST_STATUS(Resource):
    def post(self):
			payload = json.loads(request.data) #dictionary containing the credentials and another dic
						# vars which contain all the variables

			print 'payload for execution of the status call -> '
			print payload

			Apikey = payload['operationTrackingInfo']['vars']['Apikey']
			Username = payload['operationTrackingInfo']['vars']['Username']
			acc_id = payload['operationTrackingInfo']['vars']['acc_id']
			cred_id = payload['operationTrackingInfo']['vars']['cred_id']

			dic = {}
			dic['vars'] = payload['operationTrackingInfo']['vars']

			if dic['vars']['action'] == 'StartInstances' or dic['vars']['action'] == 'StopInstances':
				previous_state = payload['operationTrackingInfo']['previous_state']

			#--------------------------------------extracting credentials------------------------------------


			head = {'Apikey':Apikey, 'Username':Username}
            		request_url = 'https://partner-dev2-api.gravitant.net/cb-credential-service/api/v2.0/accounts/'+acc_id+'/credentials?credentialId='+cred_id

            		response = requests.get(request_url, headers=head)
			#storing response of the url in a var
			if str(response.status_code)[0]=='4':
				print
				print 'INVALID CREDENTIALS i.e. ANY OF (APIKEY, USERNAME, ACCOUNT_ID, CREDENTIAL_ID)'
				print
				sys.exit()

			if str(response.status_code)[0]=='5':
                                print
                                print 'AWS SERVER ERROR, TRY AGAIN LATER'
                                print
                                sys.exit()

            		dic['aws_access_key'] = (json.loads(str(response.content)))['credentials'][0]['passwordFields']['accessKey']
			dic['aws_secret_key'] = (json.loads(str(response.content)))['credentials'][0]['passwordFields']['secretKey']

			statustemplate = payload['operationTrackingInfo']['statusTemplate']
			statplayheader = {'template': statustemplate }


#----------------------------------------------------------calling api to execute statusplay------------------------------------------------------
			statusplay = requests.post(url='http://localhost:5000/aws/ansible/executePlay', headers=statplayheader, data=json.dumps(dic))

			if str(statusplay.status_code)[0]=='4' or str(statusplay.status_code)[0]=='5':
				print 
				print '-----------------------SYNTAX ERROR----------------------'
				print 'INCORRECT ANSIBLE STATUS PLAYBOOK INPUT, KINDLY TRY AGAIN'
				print
				return 'exit'
                                sys.exit()


			body = payload

			body['status'] = 'Completed'

			if dic['vars']['action'] == 'StartInstances' or dic['vars']['action'] == 'StopInstances':
                                new_state = (json.loads(statusplay.content))['current_state']
                                if new_state == 'pending' or new_state == 'stopping':
                                        status_state = 'InProgress'

                                else:
                                        if new_state == 'stopped' and previous_state == 'stopped' and dic['vars']['action'] == 'StopInstances':
                                                status_state = 'Completed'

                                        elif new_state == 'stopped' and previous_state == 'stopped' and dic['vars']['action'] == 'StartInstances':
                                                status_state = 'Failed'

					elif new_state == 'running' and previous_state == 'stopped' and dic['vars']['action'] == 'StopInstances':
                                                status_state = 'Failed'

                                        elif new_state == 'running' and previous_state == 'stopped' and dic['vars']['action'] == 'StartInstances':
                                                status_state = 'Completed'

                                        elif new_state == 'stopped' and previous_state == 'running' and dic['vars']['action'] == 'StopInstances':
                                                status_state = 'Completed'

                                        elif new_state == 'stopped' and previous_state == 'running' and dic['vars']['action'] == 'StartInstances':
                                                status_state = 'Failed'

                                        elif new_state == 'running' and previous_state == 'running' and dic['vars']['action'] == 'StopInstances':
                                                status_state = 'Failed'

					elif new_state == 'running' and previous_state == 'running' and dic['vars']['action'] == 'StartInstances':
                                                status_state = 'Completed'

				body['status'] = status_state
				if status_state == 'Failed':
					body['comments'] = 'Operation has failed due to server error.'

			statbody = {}
			statbody['routingKey'] = 'operation_status_response'
			statbody['messageContent'] = body

			print statbody

			statuscurl = 'https://partner-dev2-api.gravitant.net/message/OperationStatus'
                        statusheader = {
                                         "Content-Type": "application/json",
                                         "Accept": "application/json",
                                         "Username":"bavanapa",


                                         "Apikey":"97ea0f84-d73f-5533-954f-22a4d98ae619"
                                     }

			var123 = requests.post(statuscurl, headers=statusheader, data=json.dumps(statbody))
			print var123
			print var123.content

			return body

class exe_play(Resource):
		def post(self):

			global count
			count = 0
			global xmlresponse
			xmlresponse = ''
			class ResultCallback(CallbackBase):
			    def v2_runner_on_ok(self, result, **kwargs):
			        host = result._host
				global count
				global xmlresponse
				count += 1
				if count == 2:
	        			print(json.dumps({host.name: result._result}, indent=4))
					xmlresponse = result._result['var12']['content']


			d = (request.headers)['template']
			dic = (json.loads(request.data))

			play = yaml.safe_load(base64.decodestring(d).encode('ascii')) #yaml format of the decoded template(playbook)

			json_file = json.dumps(play)
			playbook_py = json.loads(json_file) #playbook converted to python dictionary

			request_path = (playbook_py[0]['tasks'][0]['uri']['resource_path']).encode('ascii')  # returns the resource path key name value

			list = re.findall('\{{.*?\}}', request_path) #list of all variable keyname - need to be beautified

			list1 = []
			for b in list: #beautifying all the strings
			        str1=''
        			for j in range(2,len(b)-2):
        			        str1+=b[j]
        			list1.append(str1.strip())

#---------------------------------------------Defining Variables part from config file is over---------------------------------------

			method = 'GET'
			service = (dic['vars']['service_name']).encode('ascii') 
			region = (dic['vars']['region']).encode('ascii')
			host = service+'.'+region+'.amazonaws.com'
			endpoint = 'https://'+host

			for z in range(len(list)): #replacing variables with values in the resource path
	       			request_path = request_path.replace(list[z], dic['vars'][list1[z]])

			request_parameters = ((request_path).encode('ascii'))[1:]

			def sign(key, msg): #defining a function sign to encode using hash sha256
    				return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

			def getSignatureKey(key, dateStamp, regionName, serviceName): #defining a function to create signing key
	    			kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
    				kRegion = sign(kDate, regionName)
    				kService = sign(kRegion, serviceName)
    				kSigning = sign(kService, 'aws4_request')
    				return kSigning

			access_key = (dic['aws_access_key']).encode('ascii')  #taking access key from stored variables
			secret_key = (dic['aws_secret_key']).encode('ascii')  #taking secret key from stored variables

			if access_key is None or secret_key is None:
    				print('No access key is available.') #in case of no access or secret key - EXIT
    				sys.exit()

			t = datetime.datetime.utcnow()
			amzdate = t.strftime('%Y%m%dT%H%M%SZ') #defining date and time variables used for signature
			datestamp = t.strftime('%Y%m%d')

			canonical_uri = '/'

			canonical_querystring = request_parameters

			canonical_headers = 'host:' + host + '\n' + 'x-amz-date:' + amzdate + '\n'

			signed_headers = 'host;x-amz-date'

			payload_hash = hashlib.sha256(('').encode('utf-8')).hexdigest()

			canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring + '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash

			algorithm = 'AWS4-HMAC-SHA256'

			credential_scope = datestamp + '/' + region + '/' + service + '/' + 'aws4_request'

			string_to_sign = algorithm + '\n' +  amzdate + '\n' +  credential_scope + '\n' +  hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

			signing_key = getSignatureKey(secret_key, datestamp, region, service)

			signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()

			authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + credential_scope + ', ' +  'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature

			headers = {'x-amz-date':amzdate, 'Authorization':authorization_header}
			#----------------------------------------final url to be passed in uri module----------------------------------
			request_url = endpoint + '?' + canonical_querystring




#------------------------------------------running uri module in ansible playbook HARDCODED begins-------------------------------------
			context.CLIARGS = ImmutableDict(connection='local', module_path=['/to/mymodules'], forks=10, become=None,
			                                become_method=None, become_user=None, check=False, diff=False)
			# initialize needed objects
			loader = DataLoader() # Takes care of finding and reading yaml, json and ini files
			passwords = dict(vault_pass='secret')

			results_callback = ResultCallback()
			# create inventory, use path to host config file as source or hosts in a comma separated string
			inventory = InventoryManager(loader=loader, sources=['localhost'])

			# variable manager takes care of merging all the different sources to give you a unified view of variables available in each context
			variable_manager = VariableManager(loader=loader, inventory=inventory)


			beta = {'connection': 'local', 'hosts': 'localhost', 'gather_facts':'false', 
			'tasks': [{'uri': 
				       {
					'url': request_url,
                     			'headers': headers,
                     			'method': method,
                     			'return_content': 'yes'
					},
				   'name': 'D2 OPS without using SSH', 'register': 'var12'}, {'debug':{'var':'var12'}}]}



			play = Play().load(beta, variable_manager=variable_manager, loader=loader)

			# Run it - instantiate task queue manager, which takes care of forking and setting up all objects to iterate over host list and tasks
			tqm = None
		        tqm = TaskQueueManager(inventory=inventory, variable_manager=variable_manager, loader=loader, passwords=passwords, stdout_callback=results_callback) 
			result = tqm.run(play) # most interesting data for a play is actually sent to the callback's methods

			try:
				tempvar = str(dic['vars']['action'])+'Response'
				requestid = (xmltodict.parse(xmlresponse)[tempvar]['requestId']).encode('ascii')
				if dic['vars']['action'] == 'StartInstances' or dic['vars']['action'] == 'StopInstances':
					previous_state = (xmltodict.parse(xmlresponse)[tempvar]['instancesSet']['item']['previousState']['name']) .encode('ascii')
					current_state = (xmltodict.parse(xmlresponse)[tempvar]['instancesSet']['item']['currentState']['name']) .encode('ascii')
					return jsonify({'requestid' : requestid, 'xml': xmlresponse, 'previous_state': previous_state, 'current_state' : current_state})
				return jsonify({'requestid' : requestid, 'xml': xmlresponse})
			except:
				return jsonify({'xml': xmlresponse})



api.add_resource(EXT_CRED, '/aws/ansible/executeOperation')
api.add_resource(POST_STATUS, '/aws/ansible/statusOperation')
api.add_resource(exe_play, '/aws/ansible/executePlay')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
