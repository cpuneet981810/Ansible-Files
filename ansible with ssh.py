import requests
import os
import ast
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


app = Flask(__name__) 

@app.route('/', methods=['POST', 'GET'])
def index():
	    if request.method == 'POST':





	    		final=request.data
	    		beta=ast.literal_eval(str(final))



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

               	        dic = {}
        	        dic['aws_access_key'] = (json.loads(str(response.content)))['credentials'][0]['passwordFields']['accessKey']
			dic['aws_secret_key'] = (json.loads(str(response.content)))['credentials'][0]['passwordFields']['secretKey']

			print beta

			beta['tasks'][0]['ec2']['aws_access_key'] = dic['aws_access_key']
			beta['tasks'][0]['ec2']['aws_secret_key'] = dic['aws_secret_key']

			print beta

			context.CLIARGS = ImmutableDict(module_path=['/to/mymodules'], forks=10, become=None,
			                                become_method=None, become_user=None, check=False, diff=False, inventory_path=['/etc/ansible/hosts'])
			# initialize needed objects
			loader = DataLoader() # Takes care of finding and reading yaml, json and ini files
			passwords = dict(vault_pass='secret')


			# create inventory, use path to host config file as source or hosts in a comma separated string
			inventory = InventoryManager(loader=loader, sources='akhilaws,')

			# variable manager takes care of merging all the different sources to give you a unified view of variables available in each context
			variable_manager = VariableManager(loader=loader, inventory=inventory)


			play = Play().load(beta, variable_manager=variable_manager, loader=loader)

			# Run it - instantiate task queue manager, which takes care of forking and setting up all objects to iterate over host list and tasks
			tqm = None
			try:
			        tqm = TaskQueueManager(inventory=inventory, variable_manager=variable_manager, loader=loader, passwords=passwords) 
				result = tqm.run(play) # most interesting data for a play is actually sent to the callback's methods
			finally:
			    # we always need to cleanup child procs and the structures we use to communicate with them
				if tqm is not None:
				    tqm.cleanup()

			    # Remove ansible tmpdir
			shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)

			if 'stop' not in str(final): #checking if the server is stopped, getting new ip command wont get executed if machine is being stopped or is currently powered off
				print
				print ('Processing IP and printing it...')
				new_ip = os.popen('aws ec2 describe-instances --instance-ids i-0b7ca4b790357709e --region us-east-2 --query \'Reservations[*].Instances[*].PublicIpAddress\' --output text').read()
				print new_ip

				print
				print ('Updating hosts file by saving in the new ip...')
				with open('/etc/ansible/hosts') as var1:
					lines = var1.readlines()
				with open('/etc/ansible/hosts', 'w') as var2:
					var2.writelines(lines[0])
					var2.writelines('ec2-user@'+str(new_ip))
				print ('hosts file updated. ^_^')
				print

				return jsonify({'Successful' : new_ip})

			return jsonify({'stop found' : 'no new ip returned'})

	    else:
	    	return jsonify({'get_method':'kindly switch to post method to perform d2 ops'})
if __name__=='__main__':
	app.run(debug=True)
