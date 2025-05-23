#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License. See accompanying LICENSE file.
#

import os
import re
import sys
import errno
import shlex
import logging
import platform
import subprocess
import fileinput
import getpass
from os.path import basename
from subprocess import Popen,PIPE
from datetime import date
import time
try: input = raw_input
except NameError: pass
globalDict = {}

os_name = platform.system()
os_name = os_name.upper()

is_unix = os_name == "LINUX" or os_name == "DARWIN"

jisql_debug=True
masked_pwd_string='********'

RANGER_ADMIN_HOME = os.getenv("RANGER_ADMIN_HOME")
if RANGER_ADMIN_HOME is None:
	RANGER_ADMIN_HOME = os.getcwd()

RANGER_ADMIN_CONF = os.getenv("RANGER_ADMIN_CONF")
if RANGER_ADMIN_CONF is None:
	if is_unix:
		RANGER_ADMIN_CONF = RANGER_ADMIN_HOME
	elif os_name == "WINDOWS":
		RANGER_ADMIN_CONF = os.path.join(RANGER_ADMIN_HOME,'bin')

def check_output(query):
	if is_unix:
		p = subprocess.Popen(shlex.split(query), stdout=subprocess.PIPE)
	elif os_name == "WINDOWS":
		p = subprocess.Popen(query, stdout=subprocess.PIPE, shell=True)
	output = p.communicate ()[0]
	return output.decode()

def log(msg,type):
	if type == 'info':
		logging.info(" %s",msg)
	if type == 'debug':
		logging.debug(" %s",msg)
	if type == 'warning':
		logging.warning(" %s",msg)
	if type == 'exception':
		logging.exception(" %s",msg)
	if type == 'error':
		logging.error(" %s",msg)

def populate_global_dict():
	global globalDict
	if is_unix:
		read_config_file = open(os.path.join(RANGER_ADMIN_CONF,'install.properties'))
	elif os_name == "WINDOWS":
		read_config_file = open(os.path.join(RANGER_ADMIN_CONF,'install_config.properties'))
		library_path = os.path.join(RANGER_ADMIN_HOME,"cred","lib","*")
	for cireach_line in read_config_file.read().split('\n') :
		each_line = cireach_line.strip()
		if len(each_line) == 0:
			continue
		elif each_line[0] == "#":
			continue
		if re.search('=', each_line):
			key , value = each_line.split("=",1)
			key = key.strip()
			if 'PASSWORD' in key:
				jceks_file_path = os.path.join(RANGER_ADMIN_HOME, 'jceks','ranger_db.jceks')
				#statuscode,value = call_keystore(library_path,key,'',jceks_file_path,'get')
				#if statuscode == 1:
				value = ''
			value = value.strip()
			globalDict[key] = value

def logFile(msg):
	if globalDict["dryMode"]==True:
		logFileName=globalDict["dryModeOutputFile"]
		if logFileName !="":
			if os.path.isfile(logFileName):
				if os.access(logFileName, os.W_OK):
					with open(logFileName, "a") as f:
						f.write(msg+"\n")
						f.close()
				else:
					log("[E] Unable to open file "+logFileName+" in write mode, Check file permissions.", "error")
					sys.exit()
			else:
				log("[E] "+logFileName+" is Invalid input file name! Provide valid file path to write DBA scripts:", "error")
				sys.exit()
		else:
			log("[E] Invalid input! Provide file path to write DBA scripts:", "error")
			sys.exit()

def password_validation(password, userType):
	if password:
		if re.search("[\\`'\"]",password):
			log("[E] "+userType+" user password contains one of the unsupported special characters like \" ' \\ `","error")
			sys.exit(1)
		else:
			log("[I] "+userType+" user password validated","info")
	else:
		if userType == "DBA root":
			log("[I] "+userType+" user password validated","info")
		else:
			log("[E] Blank password is not allowed,please enter valid password.","error")
			sys.exit(1)

def jisql_log(query, db_root_password):
	if jisql_debug == True:
		if os_name == "WINDOWS":
			query = query.replace(' -p "'+db_root_password+'"' , ' -p "'+masked_pwd_string+'"')
			log("[JISQL] "+query, "info")
		else:
			query = query.replace(" -p '"+db_root_password+"'" , " -p '"+masked_pwd_string+"'")
			log("[JISQL] "+query, "info")

def subprocessCallWithRetry(query):
	retryCount=1
	returnCode = subprocess.call(query)
	while returnCode!=0:
		retryCount=retryCount+1
		time.sleep(1)
		log("[I] SQL statement execution failed!! retrying attempt "+str(retryCount)+" of total 3" ,"info")
		returnCode = subprocess.call(query)
		if(returnCode!=0 and retryCount>=3):
			break
	return returnCode

class BaseDB(object):

	def create_rangerdb_user(self, root_user, db_user, db_password, db_root_password,dryMode):
		log("[I] ---------- Creating user ----------", "info")

	def check_connection(self, db_name, db_user, db_password):
		log("[I] ---------- Verifying DB connection ----------", "info")

	def create_db(self, root_user, db_root_password, db_name, db_user, db_password,dryMode):
		log("[I] ---------- Verifying database ----------", "info")

	def create_auditdb_user(self, xa_db_host, audit_db_host, db_name, audit_db_name, xa_db_root_user, audit_db_root_user, db_user, audit_db_user, xa_db_root_password, audit_db_root_password, db_password, audit_db_password, DBA_MODE, dryMode):
		log("[I] ---------- Create audit user ----------", "info")


class MysqlConf(BaseDB):
	# Constructor
	def __init__(self, host,SQL_CONNECTOR_JAR,JAVA_BIN,db_ssl_enabled,db_ssl_required,db_ssl_verifyServerCertificate,javax_net_ssl_keyStore,javax_net_ssl_keyStorePassword,javax_net_ssl_trustStore,javax_net_ssl_trustStorePassword,db_ssl_auth_type):
		self.host = host.lower()
		self.SQL_CONNECTOR_JAR = SQL_CONNECTOR_JAR
		self.JAVA_BIN = JAVA_BIN
		self.db_ssl_enabled=db_ssl_enabled.lower()
		self.db_ssl_required=db_ssl_required.lower()
		self.db_ssl_verifyServerCertificate=db_ssl_verifyServerCertificate.lower()
		self.db_ssl_auth_type=db_ssl_auth_type.lower()
		self.javax_net_ssl_keyStore=javax_net_ssl_keyStore
		self.javax_net_ssl_keyStorePassword=javax_net_ssl_keyStorePassword
		self.javax_net_ssl_trustStore=javax_net_ssl_trustStore
		self.javax_net_ssl_trustStorePassword=javax_net_ssl_trustStorePassword

	def get_jisql_cmd(self, user, password ,db_name):
		#TODO: User array for forming command
		path = RANGER_ADMIN_HOME
		db_ssl_param=''
		db_ssl_cert_param=''
		if self.db_ssl_enabled == 'true':
			db_ssl_param="?useSSL=%s&requireSSL=%s&verifyServerCertificate=%s" %(self.db_ssl_enabled,self.db_ssl_required,self.db_ssl_verifyServerCertificate)
			if self.db_ssl_verifyServerCertificate == 'true':
				if self.db_ssl_auth_type == '1-way':
					db_ssl_cert_param=" -Djavax.net.ssl.trustStore=%s -Djavax.net.ssl.trustStorePassword=%s " %(self.javax_net_ssl_trustStore,self.javax_net_ssl_trustStorePassword)
				else:
					db_ssl_cert_param=" -Djavax.net.ssl.keyStore=%s -Djavax.net.ssl.keyStorePassword=%s -Djavax.net.ssl.trustStore=%s -Djavax.net.ssl.trustStorePassword=%s " %(self.javax_net_ssl_keyStore,self.javax_net_ssl_keyStorePassword,self.javax_net_ssl_trustStore,self.javax_net_ssl_trustStorePassword)
		else:
			if "useSSL" not in db_name:
				db_ssl_param="?useSSL=false"
		if is_unix:
			jisql_cmd = "%s %s -cp %s:%s/jisql/lib/* org.apache.util.sql.Jisql -driver mysqlconj -cstring jdbc:mysql://%s/%s%s -u %s -p '%s' -noheader -trim -c \\;" %(self.JAVA_BIN,db_ssl_cert_param,self.SQL_CONNECTOR_JAR,path,self.host,db_name,db_ssl_param,user,password)
		elif os_name == "WINDOWS":
			self.JAVA_BIN = self.JAVA_BIN.strip("'")
			jisql_cmd = "%s %s -cp %s;%s\\jisql\\lib\\* org.apache.util.sql.Jisql -driver mysqlconj -cstring jdbc:mysql://%s/%s%s -u %s -p \"%s\" -noheader -trim" %(self.JAVA_BIN, db_ssl_cert_param,self.SQL_CONNECTOR_JAR, path, self.host, db_name,db_ssl_param,user, password)
		return jisql_cmd

	def verify_user(self, root_user, db_root_password, host, db_user, get_cmd,dryMode):
		if dryMode == False:
			log("[I] Verifying user " + db_user+ " for Host "+ host, "info")
		if is_unix:
			query = get_cmd + " -query \"select user from mysql.user where user='%s' and host='%s';\"" %(db_user,host)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"select user from mysql.user where user='%s' and host='%s';\" -c ;" %(db_user,host)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_user + " |"):
			return True
		else:
			return False

	def check_connection(self, db_name, db_user, db_password):
		#log("[I] Checking connection..", "info")
		get_cmd = self.get_jisql_cmd(db_user, db_password, db_name)
		if is_unix:
			query = get_cmd + " -query \"SELECT version();\""
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"SELECT version();\" -c ;"
		jisql_log(query, db_password)
		output = check_output(query)
		if output.strip('Production  |'):
			#log("[I] Checking connection passed.", "info")
			return True
		else:
			log("[E] Can't establish db connection.. Exiting.." ,"error")
			sys.exit(1)

	def create_rangerdb_user(self, root_user, db_user, db_password, db_root_password,dryMode):
		if self.check_connection('mysql', root_user, db_root_password):
			hosts_arr =["%", "localhost"]
			if not self.host == "localhost": hosts_arr.append(self.host)
			for host in hosts_arr:
				get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'mysql')
				if self.verify_user(root_user, db_root_password, host, db_user, get_cmd,dryMode):
					if dryMode == False:
						log("[I] MySQL user " + db_user + " already exists for host " + host, "info")
				else:
					if db_password == "":
						if dryMode == False:
							log("[I] MySQL user " + db_user + " does not exists for host " + host, "info")
							if is_unix:
								query = get_cmd + " -query \"create user '%s'@'%s';\"" %(db_user, host)
								jisql_log(query, db_root_password)
								ret = subprocessCallWithRetry(shlex.split(query))
							elif os_name == "WINDOWS":
								query = get_cmd + " -query \"create user '%s'@'%s';\" -c ;" %(db_user, host)
								jisql_log(query, db_root_password)
								ret = subprocessCallWithRetry(query)
							if ret == 0:
								if self.verify_user(root_user, db_root_password, host, db_user, get_cmd, dryMode):
									log("[I] MySQL user " + db_user +" created for host " + host ,"info")
								else:
									log("[E] Creating MySQL user " + db_user +" failed..","error")
									sys.exit(1)
						else:
							logFile("create user '%s'@'%s';" %(db_user, host))
					else:
						if dryMode == False:
							log("[I] MySQL user " + db_user + " does not exists for host " + host, "info")
							if is_unix:
								query = get_cmd + " -query \"create user '%s'@'%s' identified by '%s';\"" %(db_user, host, db_password)
								query_with_masked_pwd = get_cmd + " -query \"create user '%s'@'%s' identified by '%s';\"" %(db_user, host, masked_pwd_string)
								jisql_log(query_with_masked_pwd, db_root_password)
								ret = subprocessCallWithRetry(shlex.split(query))
							elif os_name == "WINDOWS":
								query = get_cmd + " -query \"create user '%s'@'%s' identified by '%s';\" -c ;" %(db_user, host, db_password)
								query_with_masked_pwd = get_cmd + " -query \"create user '%s'@'%s' identified by '%s';\" -c ;" %(db_user, host, masked_pwd_string)
								jisql_log(query_with_masked_pwd, db_root_password)
								ret = subprocessCallWithRetry(query)
							if self.verify_user(root_user, db_root_password, host, db_user, get_cmd,dryMode):
								log("[I] MySQL user " + db_user +" created for host " + host ,"info")
							else:
								log("[E] Creating MySQL user " + db_user +" failed..","error")
								sys.exit(1)
						else:
							logFile("create user '%s'@'%s' identified by '%s';" %(db_user, host,db_password))


	def verify_db(self, root_user, db_root_password, db_name,dryMode):
		if dryMode == False:
			log("[I] Verifying database " + db_name , "info")
		get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'mysql')
		if is_unix:
			query = get_cmd + " -query \"show databases like '%s';\"" %(db_name)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"show databases like '%s';\" -c ;" %(db_name)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_name + " |"):
			return True
		else:
			return False


	def create_db(self, root_user, db_root_password, db_name, db_user, db_password,dryMode):
		if self.verify_db(root_user, db_root_password, db_name,dryMode):
			if dryMode == False:
				log("[I] Database "+db_name + " already exists.","info")
		else:
			get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'mysql')
			if is_unix:
				query = get_cmd + " -query \"create database %s;\"" %(db_name)
			elif os_name == "WINDOWS":
				query = get_cmd + " -query \"create database %s;\" -c ;" %(db_name)
			if dryMode == False:
				log("[I] Database does not exist, Creating database " + db_name,"info")
				jisql_log(query, db_root_password)
				if is_unix:
					ret = subprocessCallWithRetry(shlex.split(query))
				elif os_name == "WINDOWS":
					ret = subprocessCallWithRetry(query)
				if ret != 0:
					if not self.verify_db(root_user, db_root_password, db_name,dryMode):
						log("[E] Database creation failed..","error")
						sys.exit(1)
				else:
					if self.verify_db(root_user, db_root_password, db_name,dryMode):
						log("[I] Creating database " + db_name + " succeeded", "info")
						return True
					else:
						log("[E] Database creation failed..","error")
						sys.exit(1)
			else:
				logFile("create database %s;" %(db_name))


	def grant_xa_db_user(self, root_user, db_name, db_user, db_password, db_root_password, is_revoke,dryMode):
		hosts_arr =["%", "localhost"]
		if not self.host == "localhost": hosts_arr.append(self.host)
		for host in hosts_arr:
			if dryMode == False:
				log("[I] ---------- Granting privileges TO user '"+db_user+"'@'"+host+"' on db '"+db_name+"'----------" , "info")
				get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'mysql')
				if is_unix:
					query = get_cmd + " -query \"grant all privileges on %s.* to '%s'@'%s' with grant option;\"" %(db_name,db_user, host)
					jisql_log(query, db_root_password)
					ret = subprocessCallWithRetry(shlex.split(query))
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"grant all privileges on %s.* to '%s'@'%s' with grant option;\" -c ;" %(db_name,db_user, host)
					jisql_log(query, db_root_password)
					ret = subprocessCallWithRetry(query)
				if ret == 0:
					log("[I] ---------- FLUSH PRIVILEGES ----------" , "info")
					if is_unix:
						query = get_cmd + " -query \"FLUSH PRIVILEGES;\""
						jisql_log(query, db_root_password)
						ret = subprocessCallWithRetry(shlex.split(query))
					elif os_name == "WINDOWS":
						query = get_cmd + " -query \"FLUSH PRIVILEGES;\" -c ;"
						jisql_log(query, db_root_password)
						ret = subprocessCallWithRetry(query)
					if ret == 0:
						log("[I] Privileges granted to '" + db_user + "' on '"+db_name+"'", "info")
					else:
						log("[E] Granting privileges to '" +db_user+"' failed on '"+db_name+"'", "error")
						sys.exit(1)
				else:
					log("[E] Granting privileges to '" +db_user+"' failed on '"+db_name+"'", "error")
					sys.exit(1)
			else:
				logFile("grant all privileges on %s.* to '%s'@'%s' with grant option;" %(db_name,db_user, host))

	def create_auditdb_user(self, xa_db_host, audit_db_host, db_name, audit_db_name, xa_db_root_user, audit_db_root_user, db_user, audit_db_user, xa_db_root_password, audit_db_root_password, db_password, audit_db_password, DBA_MODE,dryMode):
		is_revoke=False
		if DBA_MODE == "TRUE" :
			if dryMode == False:
				log("[I] ---------- Setup audit user ----------","info")
			self.create_rangerdb_user(audit_db_root_user, audit_db_user, audit_db_password, audit_db_root_password,dryMode)
			self.create_db(audit_db_root_user, audit_db_root_password, audit_db_name, db_user, db_password,dryMode)
			self.grant_xa_db_user(audit_db_root_user, audit_db_name, db_user, db_password, audit_db_root_password, is_revoke,dryMode)

	def writeDrymodeCmd(self, xa_db_host, audit_db_host, xa_db_root_user, xa_db_root_password, db_user, db_password, db_name, audit_db_root_user, audit_db_root_password, audit_db_user, audit_db_password, audit_db_name):
		logFile("# Login to MySQL Server from a MySQL dba user(i.e 'root') to execute below sql statements.")
		hosts_arr =["%", "localhost"]
		if not self.host == "localhost": hosts_arr.append(self.host)
		for host in hosts_arr:
			logFile("create user '%s'@'%s' identified by '%s';" %(db_user, host, db_password))
		logFile("create database %s;"%(db_name))
		for host in hosts_arr:
			logFile("grant all privileges on %s.* to '%s'@'%s' with grant option;"%(db_name, db_user, host))
		logFile("FLUSH PRIVILEGES;")
		if not db_user == audit_db_user:
			for host in hosts_arr:
				logFile("create user '%s'@'%s' identified by '%s';"%(audit_db_user, host, audit_db_password))
		if not db_name == audit_db_name:
			logFile("create database %s;"%(audit_db_name))
		if not db_name == audit_db_name:
			for host in hosts_arr:
				logFile("grant all privileges on %s.* to '%s'@'%s' with grant option;"%(audit_db_name, db_user, host))
			logFile("FLUSH PRIVILEGES;")


class OracleConf(BaseDB):
	# Constructor
	def __init__(self, host, SQL_CONNECTOR_JAR, JAVA_BIN):
		self.host = host 
		self.SQL_CONNECTOR_JAR = SQL_CONNECTOR_JAR
		self.JAVA_BIN = JAVA_BIN

	def get_jisql_cmd(self, user, password):
		#TODO: User array for forming command
		path = RANGER_ADMIN_HOME
		if not re.search('-Djava.security.egd=file:///dev/urandom', self.JAVA_BIN):
			self.JAVA_BIN = self.JAVA_BIN + " -Djava.security.egd=file:///dev/urandom "

		#if self.host.count(":") == 2:
		if self.host.count(":") == 2 or self.host.count(":") == 0:
			#jdbc:oracle:thin:@[HOST][:PORT]:SID or #jdbc:oracle:thin:@GL
			cstring="jdbc:oracle:thin:@%s" %(self.host)
		else:
			#jdbc:oracle:thin:@//[HOST][:PORT]/SERVICE
			cstring="jdbc:oracle:thin:@//%s" %(self.host)

		if is_unix:
			jisql_cmd = "%s -cp %s:%s/jisql/lib/* org.apache.util.sql.Jisql -driver oraclethin -cstring %s -u '%s' -p '%s' -noheader -trim" %(self.JAVA_BIN, self.SQL_CONNECTOR_JAR,path, cstring, user, password)
		elif os_name == "WINDOWS":
			jisql_cmd = "%s -cp %s;%s\\jisql\\lib\\* org.apache.util.sql.Jisql -driver oraclethin -cstring %s -u \"%s\" -p \"%s\" -noheader -trim" %(self.JAVA_BIN, self.SQL_CONNECTOR_JAR, path, cstring, user, password)
		return jisql_cmd

	def check_connection(self, db_name, db_user, db_password):
		log("[I] Checking connection", "info")
		get_cmd = self.get_jisql_cmd(db_user, db_password)
		if is_unix:
			query = get_cmd + " -c \\; -query \"select * from v$version;\""
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"select * from v$version;\" -c ;"
		jisql_log(query, db_password)
		output = check_output(query)
		if output.strip('Production  |'):
			log("[I] Connection success", "info")
			return True
		else:
			log("[E] Can't establish connection,Change configuration or Contact Administrator!!", "error")
			sys.exit(1)

	def verify_user(self, root_user, db_user, db_root_password,dryMode):
		if dryMode == False:
			log("[I] Verifying user " + db_user ,"info")
		get_cmd = self.get_jisql_cmd(root_user, db_root_password)		
		if is_unix:
			query = get_cmd + " -c \\; -query \"select username from all_users where upper(username)=upper('%s');\"" %(db_user)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"select username from all_users where upper(username)=upper('%s');\" -c ;" %(db_user)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_user + " |"):
			return True
		else:
			return False

	def create_rangerdb_user(self, root_user, db_user, db_password, db_root_password,dryMode):
		if self.check_connection(self, root_user, db_root_password):
			if self.verify_user(root_user, db_user, db_root_password,dryMode):
				if dryMode == False:
					log("[I] Oracle user " + db_user + " already exists.", "info")
			else:
				if dryMode == False:
					log("[I] User does not exists, Creating user : " + db_user, "info")
					get_cmd = self.get_jisql_cmd(root_user, db_root_password)
					if is_unix:
						query = get_cmd + " -c \\; -query 'create user %s identified by \"%s\";'" %(db_user, db_password)
						query_with_masked_pwd = get_cmd + " -c \\; -query 'create user %s identified by \"%s\";'" %(db_user,masked_pwd_string)
						jisql_log(query_with_masked_pwd, db_root_password)
						ret = subprocessCallWithRetry(shlex.split(query))
					elif os_name == "WINDOWS":
						query = get_cmd + " -query \"create user %s identified by \"%s\";\" -c ;" %(db_user, db_password)
						query_with_masked_pwd = get_cmd + " -query \"create user %s identified by \"%s\";\" -c ;" %(db_user, masked_pwd_string)
						jisql_log(query_with_masked_pwd, db_root_password)
						ret = subprocessCallWithRetry(query)
					if self.verify_user(root_user, db_user, db_root_password,dryMode):
						log("[I] User " + db_user + " created", "info")
						log("[I] Granting permission to " + db_user, "info")
						if is_unix:
							query = get_cmd + " -c \\; -query 'GRANT CREATE SESSION,CREATE PROCEDURE,CREATE TABLE,CREATE VIEW,CREATE SEQUENCE,CREATE SYNONYM,CREATE TRIGGER,UNLIMITED Tablespace TO %s;'" % (db_user)
							jisql_log(query, db_root_password)
							ret = subprocessCallWithRetry(shlex.split(query))
						elif os_name == "WINDOWS":
							query = get_cmd + " -query \"GRANT CREATE SESSION,CREATE PROCEDURE,CREATE TABLE,CREATE VIEW,CREATE SEQUENCE,CREATE SYNONYM,CREATE TRIGGER,UNLIMITED Tablespace TO %s;\" -c ;" % (db_user)
							jisql_log(query, db_root_password)
							ret = subprocessCallWithRetry(query)
						if ret == 0:
							log("[I] Granting permissions to Oracle user '" + db_user + "' for %s done" %(self.host), "info")
						else:
							log("[E] Granting permissions to Oracle user '" + db_user + "' failed..", "error")
							sys.exit(1)
					else:
						log("[E] Creating Oracle user '" + db_user + "' failed..", "error")
						sys.exit(1)
				else:
					logFile("create user %s identified by \"%s\";" %(db_user, db_password))


	def verify_tablespace(self, root_user, db_root_password, db_name,dryMode):
		if dryMode == False:
			log("[I] Verifying tablespace " + db_name, "info")
		get_cmd = self.get_jisql_cmd(root_user, db_root_password)		
		if is_unix:
			query = get_cmd + " -c \\; -query \"SELECT DISTINCT UPPER(TABLESPACE_NAME) FROM USER_TablespaceS where UPPER(Tablespace_Name)=UPPER(\'%s\');\"" %(db_name)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"SELECT DISTINCT UPPER(TABLESPACE_NAME) FROM USER_TablespaceS where UPPER(Tablespace_Name)=UPPER(\'%s\');\" -c ;" %(db_name)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_name+' |'):
			return True
		else:
			return False

	def create_db(self, root_user, db_root_password, db_name, db_user, db_password,dryMode):
		if self.verify_tablespace(root_user, db_root_password, db_name,dryMode):
			if dryMode == False:
				log("[I] Tablespace " + db_name + " already exists.","info")
				if self.verify_user(root_user, db_user, db_root_password,dryMode):
					get_cmd = self.get_jisql_cmd(db_user ,db_password)
					if is_unix:
						query = get_cmd + " -c \\; -query 'select default_tablespace from user_users;'"
					elif os_name == "WINDOWS":
						query = get_cmd + " -query \"select default_tablespace from user_users;\" -c ;"
					jisql_log(query, db_root_password)
					output = check_output(query).strip()
					db_name = db_name.upper() +' |'
					if output == db_name:
						log("[I] User name " + db_user + " and tablespace " + db_name + " already exists.","info")
					else:
						log("[E] "+db_user + " user already assigned some other tablespace , give some other DB name.","error")
						sys.exit(1)
					#status = self.assign_tablespace(root_user, db_root_password, db_user, db_password, db_name, False)
					#return status
		else:
			if dryMode == False:
				log("[I] Tablespace does not exist. Creating tablespace: " + db_name,"info")
				get_cmd = self.get_jisql_cmd(root_user, db_root_password)
				if is_unix:
					query = get_cmd + " -c \\; -query \"create tablespace %s datafile '%s.dat' size 10M autoextend on;\"" %(db_name, db_name)
					jisql_log(query, db_root_password)
					ret = subprocessCallWithRetry(shlex.split(query))
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"create tablespace %s datafile '%s.dat' size 10M autoextend on;\" -c ;" %(db_name, db_name)
					jisql_log(query, db_root_password)
					ret = subprocessCallWithRetry(query)
				if self.verify_tablespace(root_user, db_root_password, db_name,dryMode):
					log("[I] Creating tablespace "+db_name+" succeeded", "info")
					status=True
					status = self.assign_tablespace(root_user, db_root_password, db_user, db_password, db_name, status,dryMode)
					return status
				else:
					log("[E] Creating tablespace "+db_name+" failed..", "error")
					sys.exit(1)
			else:
				logFile("create tablespace %s datafile '%s.dat' size 10M autoextend on;" %(db_name, db_name))

	def assign_tablespace(self, root_user, db_root_password, db_user, db_password, db_name, status,dryMode):
		if dryMode == False:
			log("[I] Assign default tablespace " +db_name + " to " + db_user, "info")
			# Assign default tablespace db_name
			get_cmd = self.get_jisql_cmd(root_user , db_root_password)
			if is_unix:
				query = get_cmd +" -c \\; -query 'alter user %s DEFAULT Tablespace %s;'" %(db_user, db_name)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(shlex.split(query))
			elif os_name == "WINDOWS":
				query = get_cmd +" -query \"alter user %s DEFAULT Tablespace %s;\" -c ;" %(db_user, db_name)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(query)
			if ret == 0:
				log("[I] Assigning default tablespace to user '" + db_user + "' done..", "info")
			else:
				log("[E] Assigning default tablespace to user '" + db_user + "' failed..", "error")
				sys.exit(1)
		else:
			logFile("alter user %s DEFAULT Tablespace %s;" %(db_user, db_name))


	def create_auditdb(self, audit_db_root_user, db_name ,audit_db_name, db_user, audit_db_user, db_password, audit_db_password, audit_db_root_password,dryMode):
		status1 = False
		status2 = False
		if self.verify_tablespace(audit_db_root_user, audit_db_root_password, audit_db_name,dryMode):
			if dryMode == False:
				log("[I] Tablespace " + audit_db_name + " already exists.","info")
			status1 = True
		else:
			if dryMode == False:
				log("[I] Tablespace does not exist. Creating tablespace: " + audit_db_name,"info")
				get_cmd = self.get_jisql_cmd(audit_db_root_user, audit_db_root_password)
				if is_unix:
					query = get_cmd + " -c \\; -query \"create tablespace %s datafile '%s.dat' size 10M autoextend on;\"" %(audit_db_name, audit_db_name)
					jisql_log(query, audit_db_root_password)
					ret = subprocessCallWithRetry(shlex.split(query))
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"create tablespace %s datafile '%s.dat' size 10M autoextend on;\" -c ;" %(audit_db_name, audit_db_name)
					jisql_log(query, audit_db_root_password)
					ret = subprocessCallWithRetry(query)
				if ret != 0:
					log("[E] Tablespace creation failed..","error")
					sys.exit(1)
				else:
					log("[I] Creating tablespace "+ audit_db_name + " succeeded", "info")
					status1 = True
			else:
				logFile("create tablespace %s datafile '%s.dat' size 10M autoextend on;" %(audit_db_name, audit_db_name))

		if (status1 == True):
			if dryMode == False:
				log("[I] Assign default tablespace " + audit_db_name + " to : " + audit_db_user, "info")
				# Assign default tablespace audit_db_name
				get_cmd = self.get_jisql_cmd(audit_db_root_user , audit_db_root_password)
				if is_unix:
					query = get_cmd +" -c \\; -query 'alter user %s DEFAULT Tablespace %s;'" %(audit_db_user, audit_db_name)
					jisql_log(query, audit_db_root_password)
					ret2 = subprocessCallWithRetry(shlex.split(query))
				elif os_name == "WINDOWS":
					query = get_cmd +" -query \"alter user %s DEFAULT Tablespace %s;\" -c ;" %(audit_db_user, audit_db_name)
					jisql_log(query, audit_db_root_password)
					ret2 = subprocessCallWithRetry(query)

				if (ret2 == 0):
					log("[I] Assigning default tablespace to user '" + audit_db_user + "' done..", "info")
				else:
					return False
			else:
				logFile("alter user %s DEFAULT Tablespace %s;" %(audit_db_user, audit_db_name))

	def grant_xa_db_user(self, root_user, db_name, db_user, db_password, db_root_password, invoke,dryMode):
		if dryMode == False:
			get_cmd = self.get_jisql_cmd(root_user ,db_root_password)
			if is_unix:
				query = get_cmd + " -c \\; -query 'GRANT CREATE SESSION,CREATE PROCEDURE,CREATE TABLE,CREATE VIEW,CREATE SEQUENCE,CREATE SYNONYM,CREATE TRIGGER,UNLIMITED Tablespace TO %s;'" % (db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(shlex.split(query))
			elif os_name == "WINDOWS":
				query = get_cmd + " -query \"GRANT CREATE SESSION,CREATE PROCEDURE,CREATE TABLE,CREATE VIEW,CREATE SEQUENCE,CREATE SYNONYM,CREATE TRIGGER,UNLIMITED Tablespace TO %s;\" -c ;" % (db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(query)
			if ret == 0:
				log("[I] Granted permission to " + db_user, "info")
				return True
			else:
				log("[E] Granting Oracle user '" + db_user + "' failed..", "error")
				sys.exit(1)
		else:
			logFile("GRANT CREATE SESSION,CREATE PROCEDURE,CREATE TABLE,CREATE VIEW,CREATE SEQUENCE,CREATE SYNONYM,CREATE TRIGGER,UNLIMITED Tablespace TO %s;" % (db_user))

	def create_auditdb_user(self, xa_db_host , audit_db_host , db_name ,audit_db_name, xa_db_root_user, audit_db_root_user, db_user, audit_db_user, xa_db_root_password, audit_db_root_password, db_password, audit_db_password, DBA_MODE,dryMode):
		if DBA_MODE == "TRUE":
			if dryMode == False:
				log("[I] ---------- Setup audit user ----------","info")
			#self.create_rangerdb_user(audit_db_root_user, db_user, db_password, audit_db_root_password)
			if self.verify_user(audit_db_root_user, db_user, audit_db_root_password,dryMode):
				if dryMode == False:
					log("[I] Oracle admin user " + db_user + " already exists.", "info")
			else:
				if dryMode == False:
					log("[I] User does not exists, Creating user " + db_user, "info")
					get_cmd = self.get_jisql_cmd(audit_db_root_user, audit_db_root_password)
					if is_unix:
						query = get_cmd + " -c \\; -query 'create user %s identified by \"%s\";'" %(db_user, db_password)
						query_with_masked_pwd = get_cmd + " -c \\; -query 'create user %s identified by \"%s\";'" %(db_user, masked_pwd_string)
						jisql_log(query_with_masked_pwd, audit_db_root_password)
						ret = subprocessCallWithRetry(shlex.split(query))
					elif os_name == "WINDOWS":
						query = get_cmd + " -query \"create user %s identified by \"%s\";\" -c ;" %(db_user, db_password)
						query_with_masked_pwd = get_cmd + " -query \"create user %s identified by \"%s\";\" -c ;" %(db_user, masked_pwd_string)
						jisql_log(query_with_masked_pwd, audit_db_root_password)
						ret = subprocessCallWithRetry(query)
					if self.verify_user(audit_db_root_user, db_user, audit_db_root_password,dryMode):
						log("[I] User " + db_user + " created", "info")
					else:
						log("[E] Creating Oracle user '" + db_user + "' failed..", "error")
						sys.exit(1)
				else:
					logFile("create user %s identified by \"%s\";" %(db_user, db_password))

			if self.verify_user(audit_db_root_user, audit_db_user, audit_db_root_password,dryMode):
				if dryMode == False:
					log("[I] Oracle audit user " + audit_db_user + " already exist.", "info")
			else:
				if dryMode == False:
					log("[I] Audit user does not exists, Creating audit user " + audit_db_user, "info")
					get_cmd = self.get_jisql_cmd(audit_db_root_user, audit_db_root_password)
					if is_unix:
						query = get_cmd + " -c \\; -query 'create user %s identified by \"%s\";'" %(audit_db_user, audit_db_password)
						query_with_masked_pwd = get_cmd + " -c \\; -query 'create user %s identified by \"%s\";'" %(audit_db_user, masked_pwd_string)
						jisql_log(query_with_masked_pwd, audit_db_root_password)
						ret = subprocessCallWithRetry(shlex.split(query))
					elif os_name == "WINDOWS":
						query = get_cmd + " -query \"create user %s identified by \"%s\";\" -c ;" %(audit_db_user, audit_db_password)
						query_with_masked_pwd = get_cmd + " -query \"create user %s identified by \"%s\";\" -c ;" %(audit_db_user, masked_pwd_string)
						jisql_log(query_with_masked_pwd, audit_db_root_password)
						ret = subprocessCallWithRetry(query)
					if self.verify_user(audit_db_root_user, audit_db_user, audit_db_root_password,dryMode):
						if is_unix:
							query = get_cmd + " -c \\; -query \"GRANT CREATE SESSION TO %s;\"" %(audit_db_user)
							jisql_log(query, audit_db_root_password)
							ret = subprocessCallWithRetry(shlex.split(query))
						elif os_name == "WINDOWS":
							query = get_cmd + " -query \"GRANT CREATE SESSION TO %s;\" -c ;" %(audit_db_user)
							jisql_log(query, audit_db_root_password)
							ret = subprocessCallWithRetry(query)
						if ret == 0:
							log("[I] Granting permission to " + audit_db_user + " done", "info")
						else:
							log("[E] Granting permission to " + audit_db_user + " failed..", "error")
							sys.exit(1)
					else:
						log("[I] Creating audit user " + audit_db_user + " failed..", "info")
				else:
					logFile("create user %s identified by \"%s\";" %(audit_db_user, audit_db_password))
					logFile("GRANT CREATE SESSION TO %s;" % (audit_db_user))
			self.create_auditdb(audit_db_root_user, db_name ,audit_db_name, db_user, audit_db_user, db_password, audit_db_password, audit_db_root_password,dryMode)
		if DBA_MODE == "TRUE":
			self.grant_xa_db_user(audit_db_root_user, audit_db_name, db_user, db_password, audit_db_root_password, False,dryMode)

	def writeDrymodeCmd(self, xa_db_host, audit_db_host, xa_db_root_user, xa_db_root_password, db_user, db_password, db_name, audit_db_root_user, audit_db_root_password, audit_db_user, audit_db_password, audit_db_name):
		logFile("# Login to ORACLE Server from a ORACLE dba user(i.e 'sys') to execute below sql statements.")
		logFile('create user %s identified by "%s";'%(db_user, db_password))
		logFile('GRANT CREATE SESSION,CREATE PROCEDURE,CREATE TABLE,CREATE VIEW,CREATE SEQUENCE,CREATE SYNONYM,CREATE TRIGGER,UNLIMITED TABLESPACE TO %s;'%(db_user))
		logFile("create tablespace %s datafile '%s.dat' size 10M autoextend on;" %(db_name, db_name))
		logFile('alter user %s DEFAULT tablespace %s;'%(db_user, db_name))
		if not db_user == audit_db_user:
			logFile('create user %s identified by "%s";'%(audit_db_user, audit_db_password))
			logFile('GRANT CREATE SESSION TO %s;' %(audit_db_user))
			logFile("create tablespace %s datafile '%s.dat' size 10M autoextend on;" %(audit_db_name, audit_db_name))
			logFile('alter user %s DEFAULT tablespace %s;' %(audit_db_user, audit_db_name))

class PostgresConf(BaseDB):
	# Constructor
	def __init__(self, host,SQL_CONNECTOR_JAR,JAVA_BIN,db_ssl_enabled,db_ssl_required,db_ssl_verifyServerCertificate,javax_net_ssl_keyStore,javax_net_ssl_keyStorePassword,javax_net_ssl_trustStore,javax_net_ssl_trustStorePassword,db_ssl_auth_type):
		self.host = host.lower()
		self.SQL_CONNECTOR_JAR = SQL_CONNECTOR_JAR
		self.JAVA_BIN = JAVA_BIN
		self.db_ssl_enabled=db_ssl_enabled.lower()
		self.db_ssl_required=db_ssl_required.lower()
		self.db_ssl_verifyServerCertificate=db_ssl_verifyServerCertificate.lower()
		self.db_ssl_auth_type=db_ssl_auth_type.lower()
		self.javax_net_ssl_keyStore=javax_net_ssl_keyStore
		self.javax_net_ssl_keyStorePassword=javax_net_ssl_keyStorePassword
		self.javax_net_ssl_trustStore=javax_net_ssl_trustStore
		self.javax_net_ssl_trustStorePassword=javax_net_ssl_trustStorePassword

	def get_jisql_cmd(self, user, password, db_name):
		#TODO: User array for forming command
		path = RANGER_ADMIN_HOME
		self.JAVA_BIN = self.JAVA_BIN.strip("'")
		db_ssl_param=''
		db_ssl_cert_param=''
		if self.db_ssl_enabled == 'true':
			db_ssl_param="?ssl=%s" %(self.db_ssl_enabled)
			if self.db_ssl_verifyServerCertificate == 'true' or self.db_ssl_required == 'true':
				if self.db_ssl_auth_type == '1-way':
					db_ssl_cert_param=" -Djavax.net.ssl.trustStore=%s -Djavax.net.ssl.trustStorePassword=%s " %(self.javax_net_ssl_trustStore,self.javax_net_ssl_trustStorePassword)
				else:
					db_ssl_cert_param=" -Djavax.net.ssl.keyStore=%s -Djavax.net.ssl.keyStorePassword=%s -Djavax.net.ssl.trustStore=%s -Djavax.net.ssl.trustStorePassword=%s " %(self.javax_net_ssl_keyStore,self.javax_net_ssl_keyStorePassword,self.javax_net_ssl_trustStore,self.javax_net_ssl_trustStorePassword)
			else:
				db_ssl_param="?ssl=%s&sslfactory=org.postgresql.ssl.NonValidatingFactory" %(self.db_ssl_enabled)
		if is_unix:
			jisql_cmd = "%s %s -cp %s:%s/jisql/lib/* org.apache.util.sql.Jisql -driver postgresql -cstring jdbc:postgresql://%s/%s%s -u %s -p '%s' -noheader -trim -c \\;" %(self.JAVA_BIN, db_ssl_cert_param,self.SQL_CONNECTOR_JAR,path, self.host, db_name, db_ssl_param,user, password)
		elif os_name == "WINDOWS":
			jisql_cmd = "%s %s -cp %s;%s\\jisql\\lib\\* org.apache.util.sql.Jisql -driver postgresql -cstring jdbc:postgresql://%s/%s%s -u %s -p \"%s\" -noheader -trim" %(self.JAVA_BIN, db_ssl_cert_param,self.SQL_CONNECTOR_JAR, path, self.host, db_name, db_ssl_param,user, password)
		return jisql_cmd

	def verify_user(self, root_user, db_root_password, db_user,dryMode):
		if dryMode == False:
			log("[I] Verifying user " + db_user , "info")
		get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'postgres')
		if is_unix:
			query = get_cmd + " -query \"SELECT rolname FROM pg_roles WHERE rolname='%s';\"" %(db_user)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"SELECT rolname FROM pg_roles WHERE rolname='%s';\" -c ;" %(db_user)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_user + " |"):
			return True
		else:
			return False

	def check_connection(self, db_name, db_user, db_password):
		#log("[I] Checking connection", "info")
		get_cmd = self.get_jisql_cmd(db_user, db_password, db_name)
		if is_unix:
			query = get_cmd + " -query \"SELECT 1;\""
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"SELECT 1;\" -c ;"
		jisql_log(query, db_password)
		output = check_output(query)
		if output.strip('1 |'):
			#log("[I] connection success", "info")
			return True
		else:
			log("[E] Can't establish connection, Please check connection settings or contact Administrator", "error")
			sys.exit(1)

	def create_rangerdb_user(self, root_user, db_user, db_password, db_root_password,dryMode):
		if self.check_connection('postgres', root_user, db_root_password):
			if self.verify_user(root_user, db_root_password, db_user,dryMode):
				if dryMode == False:
					log("[I] Postgres user " + db_user + " already exists.", "info")
			else:
				if dryMode == False:
					log("[I] User does not exists, Creating user : " + db_user, "info")
					get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'postgres')
					if is_unix:
						query = get_cmd + " -query \"CREATE USER \\\"%s\\\" WITH LOGIN PASSWORD '%s';\"" %(db_user, db_password)
						query_with_masked_pwd = get_cmd + " -query \"CREATE USER \\\"%s\\\" WITH LOGIN PASSWORD '%s';\"" %(db_user, masked_pwd_string)
						jisql_log(query_with_masked_pwd, db_root_password)
						ret = subprocessCallWithRetry(shlex.split(query))
					elif os_name == "WINDOWS":
						query = get_cmd + " -query \"CREATE USER \\\"%s\\\" WITH LOGIN PASSWORD '%s';\" -c ;" %(db_user, db_password)
						query_with_masked_pwd = get_cmd + " -query \"CREATE USER \\\"%s\\\" WITH LOGIN PASSWORD '%s';\" -c ;" %(db_user, masked_pwd_string)
						jisql_log(query_with_masked_pwd, db_root_password)
						ret = subprocessCallWithRetry(query)
					if self.verify_user(root_user, db_root_password, db_user,dryMode):
						log("[I] Postgres user " + db_user + " created", "info")
					else:
						log("[E] Postgres user " +db_user+" creation failed..", "error")
						sys.exit(1)
				else:
					logFile("CREATE USER \"%s\" WITH LOGIN PASSWORD '%s';" %(db_user, db_password))

	def verify_db(self, root_user, db_root_password, db_name,dryMode):
		if dryMode == False:
			log("[I] Verifying database " + db_name , "info")
		get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'postgres')
		if is_unix:
			query = get_cmd + " -query \"SELECT datname FROM pg_database where datname='%s';\"" %(db_name)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"SELECT datname FROM pg_database where datname='%s';\" -c ;" %(db_name)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_name + " |"):
			return True
		else:
			return False


	def create_db(self, root_user, db_root_password, db_name, db_user, db_password,dryMode):
		if self.verify_db(root_user, db_root_password, db_name,dryMode):
			if dryMode == False:
				log("[I] Database "+db_name + " already exists.", "info")
		else:
			if dryMode == False:
				log("[I] Database does not exist, Creating database : " + db_name,"info")
				get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'postgres')
				if is_unix:
					query = get_cmd + " -query \"create database \\\"%s\\\" with OWNER \\\"%s\\\";\"" %(db_name, db_user)
					jisql_log(query, db_root_password)
					ret = subprocessCallWithRetry(shlex.split(query))
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"create database \\\"%s\\\" with OWNER \\\"%s\\\";\" -c ;" %(db_name, db_user)
					jisql_log(query, db_root_password)
					ret = subprocessCallWithRetry(query)
				if self.verify_db(root_user, db_root_password, db_name,dryMode):
					log("[I] Creating database " + db_name + " succeeded", "info")
					return True
				else:
					log("[E] Database creation failed..","error")
					sys.exit(1)
			else:
				logFile("CREATE DATABASE \"%s\" WITH OWNER \"%s\";" %(db_name, db_user))

	def grant_xa_db_user(self, root_user, db_name, db_user, db_password, db_root_password , is_revoke,dryMode):
		if dryMode == False:
			log("[I] Granting privileges TO user '"+db_user+"' on db '"+db_name+"'" , "info")
			get_cmd = self.get_jisql_cmd(root_user, db_root_password, db_name)
			if is_unix:
				query = get_cmd + " -query \"GRANT ALL PRIVILEGES ON DATABASE \\\"%s\\\" to \\\"%s\\\";\"" %(db_name, db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(shlex.split(query))
			elif os_name == "WINDOWS":
				query = get_cmd + " -query \"GRANT ALL PRIVILEGES ON DATABASE \\\"%s\\\" to \\\"%s\\\";\" -c ;" %(db_name, db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(query)
			if ret != 0:
				log("[E] Granting all privileges on database "+db_name+" to user "+db_user+" failed..", "error")
				sys.exit(1)

			if is_unix:
				query = get_cmd + " -query \"GRANT ALL PRIVILEGES ON SCHEMA public TO \\\"%s\\\";\"" %(db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(shlex.split(query))
			elif os_name == "WINDOWS":
				query = get_cmd + " -query \"GRANT ALL PRIVILEGES ON SCHEMA public TO \\\"%s\\\";\" -c ;" %(db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(query)
			if ret != 0:
				log("[E] Granting all privileges on schema public to user "+db_user+" failed..", "error")
				sys.exit(1)

			if is_unix:
				query = get_cmd + " -query \"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \\\"%s\\\";\"" %(db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(shlex.split(query))
			elif os_name == "WINDOWS":
				query = get_cmd + " -query \"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \\\"%s\\\";\" -c ;" %(db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(query)
			if ret != 0:
				log("[E] Granting all privileges on all tables in schema public to user "+db_user+" failed..", "error")
				if is_unix:
					query = get_cmd + " -query \"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';\""
					jisql_log(query, db_root_password)
					output = check_output(query)
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';\" -c ;"
					jisql_log(query, db_root_password)
					output = check_output(query)
				for each_line in output.split('\n'):
					if len(each_line) == 0 : continue
					if re.search(' |', each_line):
						tablename , value = each_line.strip().split(" |",1)
						tablename = tablename.strip()
						if is_unix:
							query1 = get_cmd + " -query \"GRANT ALL PRIVILEGES ON TABLE %s TO \\\"%s\\\";\"" %(tablename,db_user)
							jisql_log(query1, db_root_password)
							ret = subprocessCallWithRetry(shlex.split(query1))
							if ret != 0:
								log("[E] Granting all privileges on tablename "+tablename+" to user "+db_user+" failed..", "error")
								sys.exit(1)
						elif os_name == "WINDOWS":
							query1 = get_cmd + " -query \"GRANT ALL PRIVILEGES ON TABLE %s TO \\\"%s\\\";\" -c ;" %(tablename,db_user)
							jisql_log(query1, db_root_password)
							ret = subprocessCallWithRetry(query1)
							if ret != 0:
								log("[E] Granting all privileges on tablename "+tablename+" to user "+db_user+" failed..", "error")
								sys.exit(1)


			if is_unix:
				query = get_cmd + " -query \"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \\\"%s\\\";\"" %(db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(shlex.split(query))
			elif os_name == "WINDOWS":
				query = get_cmd + " -query \"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \\\"%s\\\";\" -c ;" %(db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(query)
			if ret!=0:
				log("[E] Granting all privileges on all sequences in schema public to user "+db_user+" failed..", "error")
				if is_unix:
					query = get_cmd + " -query \"SELECT sequence_name FROM information_schema.sequences where sequence_schema='public';\""
					output = check_output(query)
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"SELECT sequence_name FROM information_schema.sequences where sequence_schema='public';\" -c ;"
					jisql_log(query, db_root_password)
					output = check_output(query)
				for each_line in output.split('\n'):
					if len(each_line) == 0 : continue
					if re.search(' |', each_line):
						sequence_name , value = each_line.strip().split(" |",1)
						sequence_name = sequence_name.strip()
						if is_unix:
							query1 = get_cmd + " -query \"GRANT ALL PRIVILEGES ON SEQUENCE %s TO \\\"%s\\\";\"" %(sequence_name,db_user)
							jisql_log(query1, db_root_password)
							ret = subprocessCallWithRetry(shlex.split(query1))
							if ret != 0:
								log("[E] Granting all privileges on sequence "+sequence_name+" to user "+db_user+" failed..", "error")
								sys.exit(1)
						elif os_name == "WINDOWS":
							query1 = get_cmd + " -query \"GRANT ALL PRIVILEGES ON SEQUENCE %s TO \\\"%s\\\";\" -c ;" %(sequence_name,db_user)
							jisql_log(query1, db_root_password)
							ret = subprocessCallWithRetry(query1)
							if ret != 0:
								log("[E] Granting all privileges on sequence "+sequence_name+" to user "+db_user+" failed..", "error")
								sys.exit(1)

			log("[I] Granting privileges TO user '"+db_user+"' on db '"+db_name+"' Done" , "info")
		else:
			logFile("GRANT ALL PRIVILEGES ON DATABASE %s to \"%s\";" %(db_name, db_user))
			logFile("GRANT ALL PRIVILEGES ON SCHEMA public TO \"%s\";" %( db_user))
			logFile("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"%s\";" %(db_user))
			logFile("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"%s\";" %(db_user))

	def create_auditdb_user(self, xa_db_host, audit_db_host, db_name, audit_db_name, xa_db_root_user, audit_db_root_user, db_user, audit_db_user, xa_db_root_password, audit_db_root_password, db_password, audit_db_password, DBA_MODE,dryMode):
		if DBA_MODE == "TRUE":
			if dryMode == False:
				log("[I] ---------- Setup audit user ----------","info")
			self.create_rangerdb_user(audit_db_root_user, db_user, db_password, audit_db_root_password,dryMode)
			self.create_rangerdb_user(audit_db_root_user, audit_db_user, audit_db_password, audit_db_root_password,dryMode)
			self.create_db(audit_db_root_user, audit_db_root_password, audit_db_name, db_user, db_password,dryMode)

		if DBA_MODE == "TRUE":
			self.grant_xa_db_user(audit_db_root_user, audit_db_name, db_user, db_password, audit_db_root_password, False,dryMode)

	def writeDrymodeCmd(self, xa_db_host, audit_db_host, xa_db_root_user, xa_db_root_password, db_user, db_password, db_name, audit_db_root_user, audit_db_root_password, audit_db_user, audit_db_password, audit_db_name):
		logFile("# Login to POSTGRES Server from a POSTGRES dba user(i.e 'postgres') to execute below sql statements.")
		logFile("CREATE USER \"%s\" WITH LOGIN PASSWORD '%s';" %(db_user, db_password))
		logFile("CREATE DATABASE \"%s\" WITH OWNER \"%s\";" %(db_name, db_user))
		logFile("# Login to POSTGRES Server from a POSTGRES dba user(i.e 'postgres') on '%s' database to execute below sql statements."%(db_name))
		logFile("GRANT ALL PRIVILEGES ON DATABASE \"%s\" TO \"%s\";" %(db_name, db_user))
		logFile("GRANT ALL PRIVILEGES ON SCHEMA public TO \"%s\";" %(db_user))
		if not db_user == audit_db_user:
			logFile("# Login to POSTGRES Server from a POSTGRES dba user(i.e 'postgres') to execute below sql statements.")
			logFile("CREATE USER \"%s\" WITH LOGIN PASSWORD \"%s\";" %(audit_db_user, audit_db_password))
		if not db_name == audit_db_name:
			if not db_user == audit_db_user:
				pass
			else:
				logFile("# Login to POSTGRES Server from a POSTGRES dba user(i.e 'postgres') to execute below sql statements.")
			logFile("CREATE DATABASE \"%s\" WITH OWNER \"%s\";" %(audit_db_name, db_user))
			logFile("# Login to POSTGRES Server from a POSTGRES dba user(i.e 'postgres') on '%s' database to execute below sql statements."%(audit_db_name))
			logFile("GRANT ALL PRIVILEGES ON DATABASE \"%s\" TO \"%s\";" %(audit_db_name, db_user))
			logFile("GRANT ALL PRIVILEGES ON SCHEMA public TO \"%s\";" %(db_user))

class SqlServerConf(BaseDB):
	# Constructor
	def __init__(self, host, SQL_CONNECTOR_JAR, JAVA_BIN, is_db_override_jdbc_connection_string, db_override_jdbc_connection_string):
		self.host = host
		self.SQL_CONNECTOR_JAR = SQL_CONNECTOR_JAR
		self.JAVA_BIN = JAVA_BIN
		self.is_db_override_jdbc_connection_string = is_db_override_jdbc_connection_string
		self.db_override_jdbc_connection_string = db_override_jdbc_connection_string

	def get_jisql_cmd(self, user, password, db_name):
		#TODO: User array for forming command
		path = RANGER_ADMIN_HOME
		self.JAVA_BIN = self.JAVA_BIN.strip("'")
		if is_unix:
			if self.is_db_override_jdbc_connection_string == 'true' and self.db_override_jdbc_connection_string is not None and len(self.db_override_jdbc_connection_string) > 0:
				jisql_cmd = "%s -cp %s:%s/jisql/lib/* org.apache.util.sql.Jisql -user %s -p '%s' -driver mssql -cstring %s -noheader -trim"%(self.JAVA_BIN, self.SQL_CONNECTOR_JAR, path, user, password, self.db_override_jdbc_connection_string)
			else:
				jisql_cmd = "%s -cp %s:%s/jisql/lib/* org.apache.util.sql.Jisql -user %s -p '%s' -driver mssql -cstring jdbc:sqlserver://%s\\;databaseName=%s -noheader -trim"%(self.JAVA_BIN, self.SQL_CONNECTOR_JAR, path,user, password, self.host,db_name)
		elif os_name == "WINDOWS":
			if self.is_db_override_jdbc_connection_string == 'true' and self.db_override_jdbc_connection_string is not None and len(self.db_override_jdbc_connection_string) > 0:
				jisql_cmd = "%s -cp %s;%s\\jisql\\lib\\* org.apache.util.sql.Jisql -user %s -p \"%s\" -driver mssql -cstring %s -noheader -trim"%(self.JAVA_BIN, self.SQL_CONNECTOR_JAR, path, user, password, self.db_override_jdbc_connection_string)
			else:
				jisql_cmd = "%s -cp %s;%s\\jisql\\lib\\* org.apache.util.sql.Jisql -user %s -p \"%s\" -driver mssql -cstring jdbc:sqlserver://%s;databaseName=%s -noheader -trim"%(self.JAVA_BIN, self.SQL_CONNECTOR_JAR, path, user, password, self.host,db_name)
		return jisql_cmd

	def verify_user(self, root_user, db_root_password, db_user,dryMode):
		if dryMode == False:
			log("[I] Verifying user " + db_user , "info")
		get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'master')
		if is_unix:
			query = get_cmd + " -c \\; -query \"select name from sys.sql_logins where name = '%s';\"" %(db_user)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"select name from sys.sql_logins where name = '%s';\" -c ;" %(db_user)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_user + " |"):
			return True
		else:
			return False

	def check_connection(self, db_name, db_user, db_password):
		log("[I] Checking connection", "info")
		get_cmd = self.get_jisql_cmd(db_user, db_password, db_name)
		if is_unix:
			query = get_cmd + " -c \\; -query \"SELECT 1;\""
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"SELECT 1;\" -c ;"
		jisql_log(query, db_password)
		output = check_output(query)
		if output.strip('1 |'):
			log("[I] Connection success", "info")
			return True
		else:
			log("[E] Can't establish connection", "error")
			sys.exit(1)

	def create_rangerdb_user(self, root_user, db_user, db_password, db_root_password,dryMode):
		if self.check_connection('master', root_user, db_root_password):
			if self.verify_user(root_user, db_root_password, db_user,dryMode):
				if dryMode == False:
					log("[I] SQL Server user " + db_user + " already exists.", "info")
			else:
				if dryMode == False:
					get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'master')
					log("[I] User does not exists, Creating Login user " + db_user, "info")
					if is_unix:
						query = get_cmd + " -c \\; -query \"CREATE LOGIN %s WITH PASSWORD = '%s';\"" %(db_user,db_password)
						query_with_masked_pwd = get_cmd + " -c \\; -query \"CREATE LOGIN %s WITH PASSWORD = '%s';\"" %(db_user,masked_pwd_string)
						jisql_log(query_with_masked_pwd, db_root_password)
						ret = subprocessCallWithRetry(shlex.split(query))
					elif os_name == "WINDOWS":
						query = get_cmd + " -query \"CREATE LOGIN %s WITH PASSWORD = '%s';\" -c ;" %(db_user,db_password)
						query_with_masked_pwd = get_cmd + " -query \"CREATE LOGIN %s WITH PASSWORD = '%s';\" -c ;" %(db_user,masked_pwd_string)
						jisql_log(query_with_masked_pwd, db_root_password)
						ret = subprocessCallWithRetry(query)
					if self.verify_user(root_user, db_root_password, db_user,dryMode):
						 log("[I] SQL Server Login " + db_user + " created", "info")
					else:
						log("[E] SQL Server Login " +db_user+" creation failed..", "error")
						sys.exit(1)
				else:
					logFile("CREATE LOGIN %s WITH PASSWORD = '%s';" %(db_user,db_password))

	def verify_db(self, root_user, db_root_password, db_name,dryMode):
		if dryMode == False:
			log("[I] Verifying database " + db_name, "info")
		get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'master')
		if is_unix:
			query = get_cmd + " -c \\; -query \"SELECT name from sys.databases where name='%s';\"" %(db_name)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"SELECT name from sys.databases where name='%s';\" -c ;" %(db_name)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_name + " |"):
			return True
		else:
			return False

	def create_db(self, root_user, db_root_password, db_name, db_user, db_password,dryMode):
		if self.verify_db(root_user, db_root_password, db_name,dryMode):
			if dryMode == False:
				log("[I] Database " + db_name + " already exists.","info")
		else:
			if dryMode == False:
				log("[I] Database does not exist. Creating database : " + db_name,"info")
				get_cmd = self.get_jisql_cmd(root_user, db_root_password, 'master')
				if is_unix:
					query = get_cmd + " -c \\; -query \"create database %s;\"" %(db_name)
					jisql_log(query, db_root_password)
					ret = subprocessCallWithRetry(shlex.split(query))
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"create database %s;\" -c ;" %(db_name)
					jisql_log(query, db_root_password)
					ret = subprocessCallWithRetry(query)
				if self.verify_db(root_user, db_root_password, db_name,dryMode):
					self.create_user(root_user, db_name ,db_user, db_password, db_root_password,dryMode)
					log("[I] Creating database " + db_name + " succeeded", "info")
					return True
				else:
					log("[E] Database creation failed..","error")
					sys.exit(1)
			else:
				logFile("create database %s;" %(db_name))

	def create_user(self, root_user, db_name ,db_user, db_password, db_root_password,dryMode):
		get_cmd = self.get_jisql_cmd(root_user, db_root_password, db_name)
		if is_unix:
			query = get_cmd + " -c \\; -query \"SELECT name FROM sys.database_principals WHERE name = N'%s';\"" %(db_user)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"SELECT name FROM sys.database_principals WHERE name = N'%s';\" -c ;" %(db_user)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_user + " |"):
			if dryMode == False:
				log("[I] User "+db_user+" exist ","info")
		else:
			if dryMode == False:
				if is_unix:
					query = get_cmd + " -c \\; -query \"CREATE USER %s for LOGIN %s;\"" %(db_user, db_user)
					jisql_log(query, db_root_password)
					ret = subprocessCallWithRetry(shlex.split(query))
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"CREATE USER %s for LOGIN %s;\" -c ;" %(db_user, db_user)
					jisql_log(query, db_root_password)
					ret = subprocessCallWithRetry(query)
				if is_unix:
					query = get_cmd + " -c \\; -query \"SELECT name FROM sys.database_principals WHERE name = N'%s';\"" %(db_user)
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"SELECT name FROM sys.database_principals WHERE name = N'%s';\" -c ;" %(db_user)
				jisql_log(query, db_root_password)
				output = check_output(query)
				if output.strip(db_user + " |"):
					log("[I] User "+db_user+" exist ","info")
				else:
					log("[E] User "+db_user+" creation failed..","error")
					sys.exit(1)
			else:
				logFile("CREATE USER %s for LOGIN %s;" %(db_user, db_user))

	def grant_xa_db_user(self, root_user, db_name, db_user, db_password, db_root_password, is_revoke,dryMode):
		if dryMode == False:
			log("[I] Granting permission to admin user '" + db_user + "' on db '" + db_name + "'" , "info")
			get_cmd = self.get_jisql_cmd(root_user, db_root_password, db_name)
			if is_unix:
				query = get_cmd + " -c \\; -query \" EXEC sp_addrolemember N'db_owner', N'%s';\"" %(db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(shlex.split(query))
			elif os_name == "WINDOWS":
				query = get_cmd + " -query \" EXEC sp_addrolemember N'db_owner', N'%s';\" -c ;" %(db_user)
				jisql_log(query, db_root_password)
				ret = subprocessCallWithRetry(query)
			if ret != 0:
				sys.exit(1)
		else:
			logFile("EXEC sp_addrolemember N'db_owner', N'%s';" %(db_user))

	def create_auditdb_user(self, xa_db_host, audit_db_host, db_name, audit_db_name, xa_db_root_user, audit_db_root_user, db_user, audit_db_user, xa_db_root_password, audit_db_root_password, db_password, audit_db_password, DBA_MODE,dryMode):
		is_revoke=False
		if DBA_MODE == "TRUE":
			if dryMode == False:
				log("[I] ---------- Setup audit user ---------- ","info")
			self.create_rangerdb_user(audit_db_root_user, db_user, db_password, audit_db_root_password,dryMode)
			#log("[I] --------- Setup audit user --------- ","info")
			self.create_rangerdb_user(audit_db_root_user, audit_db_user, audit_db_password, audit_db_root_password,dryMode)
			self.create_db(audit_db_root_user, audit_db_root_password ,audit_db_name, audit_db_user, audit_db_password,dryMode)
			self.create_user(xa_db_root_user, audit_db_name ,db_user, db_password, xa_db_root_password,dryMode)
			self.grant_xa_db_user(audit_db_root_user, audit_db_name, db_user, db_password, audit_db_root_password, is_revoke, dryMode)

	def writeDrymodeCmd(self, xa_db_host, audit_db_host, xa_db_root_user, xa_db_root_password, db_user, db_password, db_name, audit_db_root_user, audit_db_root_password, audit_db_user, audit_db_password, audit_db_name):
		logFile("# Login to MSSQL Server from a MSSQL dba user(i.e 'sa') to execute below sql statements.")
		logFile("CREATE LOGIN %s WITH PASSWORD = '%s';" %(db_user, db_password))
		logFile("create database %s;" %(db_name))
		logFile("# Login to MSSQL Server from a MSSQL dba user(i.e 'sa') on '%s' database to execute below sql statements."%(db_name))
		logFile("CREATE USER %s for LOGIN %s;" %(db_user, db_user))
		logFile("EXEC sp_addrolemember N'db_owner', N'%s';" %(db_user))
		if not db_user == audit_db_user:
			logFile("# Login to MSSQL Server from a MSSQL dba user(i.e 'sa') to execute below sql statements.")
			logFile("CREATE LOGIN %s WITH PASSWORD = '%s';" %(audit_db_user, audit_db_password))
		if not db_name == audit_db_name:
			if not db_user == audit_db_user:
				pass
			else:
				logFile("# Login to MSSQL Server from a MSSQL dba user(i.e 'sa') to execute below sql statements.")
			logFile("create database %s;"%(audit_db_name))
		if db_name == audit_db_name and db_user!=audit_db_user:
			logFile("# Login to MSSQL Server from a MSSQL dba user(i.e 'sa') on '%s' database to execute below sql statements."%(audit_db_name))
			logFile("CREATE USER %s for LOGIN %s;" %(audit_db_user, audit_db_user))
		if db_name != audit_db_name:
			logFile("# Login to MSSQL Server from a MSSQL dba user(i.e 'sa') on '%s' database to execute below sql statements."%(audit_db_name))
			if db_user==audit_db_user:
				logFile("CREATE USER %s for LOGIN %s;" %(db_user, db_user))
			else:
				logFile("CREATE USER %s for LOGIN %s;" %(audit_db_user, audit_db_user))
				logFile("CREATE USER %s for LOGIN %s;" %(db_user, db_user))
			logFile("EXEC sp_addrolemember N'db_owner', N'%s';" %(db_user))


class SqlAnywhereConf(BaseDB):
	# Constructor
	def __init__(self, host, SQL_CONNECTOR_JAR, JAVA_BIN):
		self.host = host
		self.SQL_CONNECTOR_JAR = SQL_CONNECTOR_JAR
		self.JAVA_BIN = JAVA_BIN

	def get_jisql_cmd(self, user, password, db_name):
		path = RANGER_ADMIN_HOME
		self.JAVA_BIN = self.JAVA_BIN.strip("'")
		if is_unix:
			jisql_cmd = "%s -cp %s:%s/jisql/lib/* org.apache.util.sql.Jisql -user %s -p '%s' -driver sapsajdbc4 -cstring jdbc:sqlanywhere:database=%s;host=%s -noheader -trim"%(self.JAVA_BIN, self.SQL_CONNECTOR_JAR, path,user, password,db_name,self.host)
		elif os_name == "WINDOWS":
			jisql_cmd = "%s -cp %s;%s\\jisql\\lib\\* org.apache.util.sql.Jisql -user %s -p \"%s\" -driver sapsajdbc4 -cstring jdbc:sqlanywhere:database=%s;host=%s -noheader -trim"%(self.JAVA_BIN, self.SQL_CONNECTOR_JAR, path, user, password,db_name,self.host)
		return jisql_cmd

	def verify_user(self, root_user, db_root_password, db_user,dryMode):
		if dryMode == False:
			log("[I] Verifying user " + db_user , "info")
		get_cmd = self.get_jisql_cmd(root_user, db_root_password, '')
		if is_unix:
			query = get_cmd + " -c \\; -query \"select name from syslogins where name = '%s';\"" %(db_user)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"select name from syslogins where name = '%s';\" -c ;" %(db_user)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_user + " |"):
			return True
		else:
			return False

	def check_connection(self, db_name, db_user, db_password):
		log("[I] Checking connection", "info")
		get_cmd = self.get_jisql_cmd(db_user, db_password, db_name)
		if is_unix:
			query = get_cmd + " -c \\; -query \"SELECT 1;\""
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"SELECT 1;\" -c ;"
		jisql_log(query, db_password)
		output = check_output(query)
		if output.strip('1 |'):
			log("[I] Connection success", "info")
			return True
		else:
			log("[E] Can't establish connection", "error")
			sys.exit(1)

	def create_rangerdb_user(self, root_user, db_user, db_password, db_root_password,dryMode):
		if self.check_connection('', root_user, db_root_password):
			if self.verify_user(root_user, db_root_password, db_user,dryMode):
				if dryMode == False:
					log("[I] SQL Anywhere user " + db_user + " already exists.", "info")
			else:
				if dryMode == False:
					get_cmd = self.get_jisql_cmd(root_user, db_root_password, '')
					log("[I] User does not exists, Creating Login user " + db_user, "info")
					if is_unix:
						query = get_cmd + " -c \\; -query \"CREATE USER %s IDENTIFIED BY '%s';\"" %(db_user,db_password)
						query_with_masked_pwd = get_cmd + " -c \\; -query \"CREATE USER %s IDENTIFIED BY '%s';\"" %(db_user,masked_pwd_string)
						jisql_log(query_with_masked_pwd, db_root_password)
						ret = subprocessCallWithRetry(shlex.split(query))
					elif os_name == "WINDOWS":
						query = get_cmd + " -query \"CREATE USER %s IDENTIFIED BY '%s';\" -c ;" %(db_user,db_password)
						query_with_masked_pwd = get_cmd + " -query \"CREATE USER %s IDENTIFIED BY '%s';\" -c ;" %(db_user,masked_pwd_string)
						jisql_log(query_with_masked_pwd, db_root_password)
						ret = subprocessCallWithRetry(query)
					if self.verify_user(root_user, db_root_password, db_user,dryMode):
						 log("[I] SQL Anywhere user " + db_user + " created", "info")
					else:
						log("[E] SQL Anywhere user " +db_user+" creation failed..", "error")
						sys.exit(1)
				else:
					logFile("CREATE USER %s IDENTIFIED BY '%s';" %(db_user,db_password))

	def start_db(self,root_user, db_root_password, db_name,dryMode):
		if dryMode == False:
			log("[I] Starting database " + db_name, "info")
		get_cmd = self.get_jisql_cmd(root_user, db_root_password, '')
		if is_unix:
			query = get_cmd + " -c \\; -query \"start database '%s' autostop off;\"" %(db_name)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"start database '%s' autostop off;\" -c ;" %(db_name)
		jisql_log(query, db_root_password)
		output = check_output(query)

	def verify_db(self, root_user, db_root_password, db_name,dryMode):
		if dryMode == False:
			log("[I] Verifying database " + db_name, "info")
		get_cmd = self.get_jisql_cmd(root_user, db_root_password, '')
		if is_unix:
			query = get_cmd + " -c \\; -query \"select alias from sa_db_info() where alias='%s';\"" %(db_name)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"select alias from sa_db_info() where alias='%s';\" -c ;" %(db_name)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_name + " |"):
			return True
		else:
			return False

	def create_db(self, root_user, db_root_password, db_name, db_user, db_password,dryMode):
		if self.verify_db(root_user, db_root_password, db_name,dryMode):
			if dryMode == False:
				log("[I] Database " + db_name + " already exists.","info")
		else:
			if dryMode == False:
				log("[I] Database does not exist. Creating database : " + db_name,"info")
				get_cmd = self.get_jisql_cmd(root_user, db_root_password, '')
				if is_unix:
					query = get_cmd + " -c \\; -query \"create database '%s' dba user '%s' dba password '%s' database size 100MB;\"" %(db_name,db_user, db_password)
					query_with_masked_pwd = get_cmd + " -c \\; -query \"create database '%s' dba user '%s' dba password '%s' database size 100MB;\"" %(db_name,db_user, masked_pwd_string)
					jisql_log(query_with_masked_pwd, db_root_password)
					ret = subprocessCallWithRetry(shlex.split(query))
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"create database '%s' dba user '%s' dba password '%s' database size 100MB;\" -c ;" %(db_name,db_user, db_password)
					query_with_masked_pwd = get_cmd + " -query \"create database '%s' dba user '%s' dba password '%s' database size 100MB;\" -c ;" %(db_name,db_user, masked_pwd_string)
					jisql_log(query_with_masked_pwd, db_root_password)
					ret = subprocessCallWithRetry(query)
				self.start_db(root_user, db_root_password, db_name,dryMode)
				if self.verify_db(root_user, db_root_password, db_name,dryMode):
					self.create_user(root_user, db_name ,db_user, db_password, db_root_password,dryMode)
					log("[I] Creating database " + db_name + " succeeded", "info")
					return True
				else:
					log("[E] Database creation failed..","error")
					sys.exit(1)
			else:
				logFile("create database %s dba user '%s' dba password '%s' database size 100MB;" %(db_name,db_user, db_password))

	def create_user(self, root_user, db_name ,db_user, db_password, db_root_password,dryMode):
		get_cmd = self.get_jisql_cmd(root_user, db_root_password, '')
		if is_unix:
			query = get_cmd + " -c \\; -query \"select name from syslogins where name ='%s';\"" %(db_user)
		elif os_name == "WINDOWS":
			query = get_cmd + " -query \"select name from syslogins where name ='%s';\" -c ;" %(db_user)
		jisql_log(query, db_root_password)
		output = check_output(query)
		if output.strip(db_user + " |"):
			if dryMode == False:
				log("[I] User "+db_user+" exist ","info")
		else:
			if dryMode == False:
				if is_unix:
					query = get_cmd + " -c \\; -query \"CREATE USER %s IDENTIFIED BY '%s';\"" %(db_user, db_password)
					query_with_masked_pwd = get_cmd + " -c \\; -query \"CREATE USER %s IDENTIFIED BY '%s';\"" %(db_user, masked_pwd_string)
					jisql_log(query_with_masked_pwd, db_root_password)
					ret = subprocessCallWithRetry(shlex.split(query))
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"CREATE USER %s IDENTIFIED BY '%s';\" -c ;" %(db_user, db_password)
					query_with_masked_pwd = get_cmd + " -query \"CREATE USER %s IDENTIFIED BY '%s';\" -c ;" %(db_user, masked_pwd_string)
					jisql_log(query_with_masked_pwd, db_root_password)
					ret = subprocessCallWithRetry(query)
				if is_unix:
					query = get_cmd + " -c \\; -query \"select name from syslogins where name ='%s';\"" %(db_user)
				elif os_name == "WINDOWS":
					query = get_cmd + " -query \"select name from syslogins where name ='%s';\" -c ;" %(db_user)
				jisql_log(query, db_root_password)
				output = check_output(query)
				if output.strip(db_user + " |"):
					log("[I] User "+db_user+" exist ","info")
				else:
					log("[E] User "+db_user+" creation failed..","error")
					sys.exit(1)
			else:
				logFile("CREATE USER %s IDENTIFIED BY '%s';" %(db_user, db_password))

	def grant_xa_db_user(self, root_user, db_name, db_user, db_password, db_root_password, is_revoke,dryMode):
		if dryMode == False:
			log("[I] Granting permission to user '" + db_user + "' on db '" + db_name + "'" , "info")
			get_cmd = self.get_jisql_cmd(root_user, db_root_password, db_name)
			if is_unix:
				query = get_cmd + " -c \\; -query \" GRANT CONNECT to %s IDENTIFIED BY '%s';\"" %(db_user,db_password)
				query_with_masked_pwd = get_cmd + " -c \\; -query \" GRANT CONNECT to %s IDENTIFIED BY '%s';\"" %(db_user,masked_pwd_string)
				jisql_log(query_with_masked_pwd, db_root_password)
				ret = subprocessCallWithRetry(shlex.split(query))
			elif os_name == "WINDOWS":
				query = get_cmd + " -query \" GRANT CONNECT to %s IDENTIFIED BY '%s';\"" %(db_user,db_password)
				query_with_masked_pwd = get_cmd + " -query \" GRANT CONNECT to %s IDENTIFIED BY '%s';\"" %(db_user,masked_pwd_string)
				jisql_log(query_with_masked_pwd, db_root_password)
				ret = subprocessCallWithRetry(query)
			if ret != 0:
				sys.exit(1)
		else:
			logFile("GRANT CONNECT to %s IDENTIFIED BY '%s';" %(db_user, db_password))

	def create_auditdb_user(self, xa_db_host, audit_db_host, db_name, audit_db_name, xa_db_root_user, audit_db_root_user, db_user, audit_db_user, xa_db_root_password, audit_db_root_password, db_password, audit_db_password, DBA_MODE,dryMode):
		is_revoke=False
		if DBA_MODE == "TRUE":
			if dryMode == False:
				log("[I] ---------- Setup audit user ---------- ","info")
			self.create_rangerdb_user(audit_db_root_user, db_user, db_password, audit_db_root_password,dryMode)
			self.create_rangerdb_user(audit_db_root_user, audit_db_user, audit_db_password, audit_db_root_password,dryMode)
			self.create_db(audit_db_root_user, audit_db_root_password ,audit_db_name, db_user, db_password,dryMode)
			self.create_user(xa_db_root_user, audit_db_name ,db_user, db_password, xa_db_root_password,dryMode)
			self.grant_xa_db_user(db_user, audit_db_name, audit_db_user, audit_db_password, db_password, is_revoke, dryMode)

	def writeDrymodeCmd(self, xa_db_host, audit_db_host, xa_db_root_user, xa_db_root_password, db_user, db_password, db_name, audit_db_root_user, audit_db_root_password, audit_db_user, audit_db_password, audit_db_name):
		logFile("# Login to SQL Anywhere Server from a SQLA dba user(i.e 'dba') to execute below sql statements.")
		logFile("CREATE USER %s IDENTIFIED BY '%s';" %(db_user, db_password))
		logFile("create database '%s' dba user '%s' dba password '%s' database size 100MB;" %(db_name, db_user ,db_password))
		logFile("start database '%s' autostop off;" %(db_name))
		if not db_user == audit_db_user:
			logFile("CREATE USER %s IDENTIFIED BY '%s';" %(audit_db_user, audit_db_password))
		if not db_name == audit_db_name:
			logFile("create database '%s' dba user '%s' dba password '%s' database size 100MB;" %(audit_db_name, db_user ,db_password))
			logFile("start database '%s' autostop off;" %(audit_db_name))
		if not db_user == audit_db_user:
			logFile("# Login to SQL Anywhere Server from '%s' user on '%s' database to execute below sql statements."%(db_user,audit_db_name))
			logFile("GRANT CONNECT to %s IDENTIFIED BY '%s';" %(audit_db_user, audit_db_password))

def main(argv):

	FORMAT = '%(asctime)-15s %(message)s'
	logging.basicConfig(format=FORMAT, level=logging.DEBUG)
	DBA_MODE = 'TRUE'

	quiteMode = False
	dryMode=False
	is_revoke=False

	if len(argv) == 4 and argv[3] == 'password_validation':
			password_validation(argv[1],argv[2]);
			return;

	if len(argv) > 1:
		for i in range(len(argv)):
			if str(argv[i]) == "-q":
				quiteMode = True
				populate_global_dict()
			if str(argv[i]) == "-d":
				index=i+1
				try:
					dba_sql_file=str(argv[index])
					if dba_sql_file == "":
						log("[E] Invalid input! Provide file path to write DBA scripts:","error")
						sys.exit(1)
				except IndexError:
					log("[E] Invalid input! Provide file path to write DBA scripts:","error")
					sys.exit(1)

				if not dba_sql_file == "":
					if not os.path.exists(dba_sql_file):
						log("[I] Creating File:"+dba_sql_file,"info")
						open(dba_sql_file, 'w').close()
					else:
						log("[I] File "+dba_sql_file+ " is available.","info")

					if os.path.isfile(dba_sql_file):
						dryMode=True
						globalDict["dryMode"]=True
						globalDict["dryModeOutputFile"]=dba_sql_file
					else:
						log("[E] Invalid file Name! Unable to find file:"+dba_sql_file,"error")
						sys.exit(1)

	log("[I] Running DBA setup script. QuiteMode:" + str(quiteMode),"info")
	if (quiteMode):
		if (not 'JAVA_HOME' in os.environ) or (os.environ['JAVA_HOME'] == ""):
			log("[E] ---------- JAVA_HOME environment property not defined, aborting installation. ----------", "error")
			sys.exit(1)
		else:
			JAVA_BIN=os.path.join(os.environ['JAVA_HOME'],'bin','java')
		if os_name == "WINDOWS" :
			JAVA_BIN = JAVA_BIN+'.exe'
		if os.path.isfile(JAVA_BIN):
			pass
		else:
			JAVA_BIN=globalDict['JAVA_BIN']
			if os.path.isfile(JAVA_BIN):
				pass
			else:
				log("[E] ---------- JAVA Not Found, aborting installation. ----------", "error")
				sys.exit(1)
		log("[I] Using Java:" + str(JAVA_BIN),"info")
	else:
		JAVA_BIN=''
		if not dryMode:
			if (not 'JAVA_HOME' in os.environ) or (os.environ['JAVA_HOME'] == ""):
				log("[E] ---------- JAVA_HOME environment property not defined, aborting installation. ----------", "error")
				sys.exit(1)
			JAVA_BIN=os.path.join(os.environ['JAVA_HOME'],'bin','java')
			if os_name == "WINDOWS" :
				JAVA_BIN = JAVA_BIN+'.exe'
			if os.path.isfile(JAVA_BIN):
				pass
			else :
				while os.path.isfile(JAVA_BIN) == False:
					log("Enter java executable path: :","info")
					JAVA_BIN=input()
			log("[I] Using Java:" + str(JAVA_BIN),"info")


	if (quiteMode):
		XA_DB_FLAVOR=globalDict['DB_FLAVOR']
		AUDIT_DB_FLAVOR=globalDict['DB_FLAVOR']
	else:
		XA_DB_FLAVOR=''
		while XA_DB_FLAVOR == "":
			log("Enter db flavour{MYSQL|ORACLE|POSTGRES|MSSQL|SQLA} :","info")
			XA_DB_FLAVOR=input()
			AUDIT_DB_FLAVOR = XA_DB_FLAVOR

	XA_DB_FLAVOR = XA_DB_FLAVOR.upper()
	AUDIT_DB_FLAVOR = AUDIT_DB_FLAVOR.upper()
	log("[I] DB FLAVOR:" + str(XA_DB_FLAVOR),"info")

	if (quiteMode):
		CONNECTOR_JAR=globalDict['SQL_CONNECTOR_JAR']
	else:
		CONNECTOR_JAR=''
		if not dryMode:
			if XA_DB_FLAVOR == "MYSQL" or XA_DB_FLAVOR == "ORACLE" or XA_DB_FLAVOR == "POSTGRES" or XA_DB_FLAVOR == "MSSQL" or XA_DB_FLAVOR == "SQLA":
				log("Enter JDBC connector file for :"+XA_DB_FLAVOR,"info")
				CONNECTOR_JAR=input()
				while os.path.isfile(CONNECTOR_JAR) == False:
					log("JDBC connector file "+CONNECTOR_JAR+" does not exist, Please enter connector path :","error")
					CONNECTOR_JAR=input()
			else:
				log("[E] ---------- NO SUCH SUPPORTED DB FLAVOUR.. ----------", "error")
				sys.exit(1)

	if (quiteMode):
		xa_db_host = globalDict['db_host']
		audit_db_host = globalDict['db_host']
		log("[I] DB Host:" + str(xa_db_host),"info")
	else:
		if (dryMode):
			xa_db_host='127.0.0.1'
			audit_db_host='127.0.0.1'
		else:
			xa_db_host=''
			while xa_db_host == "":
				log("Enter DB Host :","info")
				xa_db_host=input()
				audit_db_host=xa_db_host
			log("[I] DB Host:" + str(xa_db_host),"info")

	if (quiteMode):
		xa_db_root_user = globalDict['db_root_user']
		xa_db_root_password = globalDict['db_root_password']
	else:
		if (dryMode):
			xa_db_root_user='db_root_user'
			xa_db_root_password=masked_pwd_string
		else:
			xa_db_root_user=''
			while xa_db_root_user == "":
				log("Enter db root user:","info")
				xa_db_root_user=input()
				log("Enter db root password:","info")
				xa_db_root_password = getpass.getpass("Enter db root password:")

	if (quiteMode):
		db_name = globalDict['db_name']
	else:
		if (dryMode):
			db_name='ranger_db'
		else:
			db_name = ''
			while db_name == "":
				log("Enter DB Name :","info")
				db_name=input()

	if (quiteMode):
		db_user = globalDict['db_user']
	else:
		if (dryMode):
			db_user='ranger_admin_user'
		else:
			db_user=''
			while db_user == "":
				log("Enter db user name:","info")
				db_user=input()

	if (quiteMode):
		db_password = globalDict['db_password']
	else:
		if (dryMode):
			db_password=masked_pwd_string
		else:
			db_password=''
			while db_password == "":
				log("Enter db user password:","info")
				db_password = getpass.getpass("Enter db user password:")

	audit_db_name=''
	audit_db_user=''
	audit_db_password=''
	audit_store = None
	if 'audit_store' in globalDict:
		audit_store = globalDict['audit_store']
		audit_store=audit_store.lower()

	if audit_store =='db':
		if (quiteMode):
			if 'audit_db_name' in globalDict:
				audit_db_name = globalDict['audit_db_name']
		else:
			if (dryMode):
				audit_db_name='ranger_audit_db'
			else:
				audit_db_name=''
				while audit_db_name == "":
					log("Enter audit db name:","info")
					audit_db_name = input()

		if (quiteMode):
			if 'audit_db_user' in globalDict:
				audit_db_user = globalDict['audit_db_user']
		else:
			if (dryMode):
				audit_db_user='ranger_logger_user'
			else:
				audit_db_user=''
				while audit_db_user == "":
					log("Enter audit user name:","info")
					audit_db_user = input()

		if (quiteMode):
			if 'audit_db_password' in globalDict:
				audit_db_password = globalDict['audit_db_password']
		else:
			if (dryMode):
				audit_db_password=masked_pwd_string
			else:
				audit_db_password=''
				while audit_db_password == "":
					log("Enter audit db user password:","info")
					audit_db_password = getpass.getpass("Enter audit db user password:")

	audit_db_root_user = xa_db_root_user
	audit_db_root_password = xa_db_root_password

	mysql_dbversion_catalog = os.path.join('db','mysql','create_dbversion_catalog.sql')
	mysql_core_file = os.path.join('db','mysql','xa_core_db.sql')
	mysql_audit_file = os.path.join('db','mysql','xa_audit_db.sql')
	mysql_patches = os.path.join('db','mysql','patches')

	oracle_dbversion_catalog = os.path.join('db','oracle','create_dbversion_catalog.sql')
	oracle_core_file = os.path.join('db','oracle','xa_core_db_oracle.sql')
	oracle_audit_file = os.path.join('db','oracle','xa_audit_db_oracle.sql')
	oracle_patches = os.path.join('db','oracle','patches')

	postgres_dbversion_catalog = os.path.join('db','postgres','create_dbversion_catalog.sql')
	postgres_core_file = os.path.join('db','postgres','xa_core_db_postgres.sql')
	postgres_audit_file = os.path.join('db','postgres','xa_audit_db_postgres.sql')
	postgres_patches = os.path.join('db','postgres','patches')

	sqlserver_dbversion_catalog = os.path.join('db','sqlserver','create_dbversion_catalog.sql')
	sqlserver_core_file = os.path.join('db','sqlserver','xa_core_db_sqlserver.sql')
	sqlserver_audit_file = os.path.join('db','sqlserver','xa_audit_db_sqlserver.sql')
	sqlserver_patches = os.path.join('db','sqlserver','patches')

	sqlanywhere_dbversion_catalog = os.path.join('db','sqlanywhere','create_dbversion_catalog.sql')
	sqlanywhere_core_file = os.path.join('db','sqlanywhere','xa_core_db_sqlanywhere.sql')
	sqlanywhere_audit_file = os.path.join('db','sqlanywhere','xa_audit_db_sqlanywhere.sql')
	sqlanywhere_patches = os.path.join('db','sqlanywhere','patches')

	x_db_version = 'x_db_version_h'
	xa_access_audit = 'xa_access_audit'
	x_user = 'x_portal_user'

	db_ssl_enabled='false'
	db_ssl_required='false'
	db_ssl_verifyServerCertificate='false'
	db_ssl_auth_type='2-way'
	javax_net_ssl_keyStore=''
	javax_net_ssl_keyStorePassword=''
	javax_net_ssl_trustStore=''
	javax_net_ssl_trustStorePassword=''
	if XA_DB_FLAVOR == "MYSQL" or XA_DB_FLAVOR == "POSTGRES":
		if 'db_ssl_enabled' in globalDict:
			db_ssl_enabled=globalDict['db_ssl_enabled'].lower()
			if db_ssl_enabled == 'true':
				if 'db_ssl_required' in globalDict:
					db_ssl_required=globalDict['db_ssl_required'].lower()
				if 'db_ssl_verifyServerCertificate' in globalDict:
					db_ssl_verifyServerCertificate=globalDict['db_ssl_verifyServerCertificate'].lower()
				if 'db_ssl_auth_type' in globalDict:
					db_ssl_auth_type=globalDict['db_ssl_auth_type'].lower()
				if db_ssl_verifyServerCertificate == 'true':
					if 'javax_net_ssl_trustStore' in globalDict:
						javax_net_ssl_trustStore=globalDict['javax_net_ssl_trustStore']
					if 'javax_net_ssl_trustStorePassword' in globalDict:
						javax_net_ssl_trustStorePassword=globalDict['javax_net_ssl_trustStorePassword']
					if not os.path.exists(javax_net_ssl_trustStore):
						log("[E] Invalid file Name! Unable to find truststore file:"+javax_net_ssl_trustStore,"error")
						sys.exit(1)
					if javax_net_ssl_trustStorePassword is None or javax_net_ssl_trustStorePassword =="":
						log("[E] Invalid ssl truststore password!","error")
						sys.exit(1)
					if db_ssl_auth_type == '2-way':
						if 'javax_net_ssl_keyStore' in globalDict:
							javax_net_ssl_keyStore=globalDict['javax_net_ssl_keyStore']
						if 'javax_net_ssl_keyStorePassword' in globalDict:
							javax_net_ssl_keyStorePassword=globalDict['javax_net_ssl_keyStorePassword']
						if not os.path.exists(javax_net_ssl_keyStore):
							log("[E] Invalid file Name! Unable to find keystore file:"+javax_net_ssl_keyStore,"error")
							sys.exit(1)
						if javax_net_ssl_keyStorePassword is None or javax_net_ssl_keyStorePassword =="":
							log("[E] Invalid ssl keystore password!","error")
							sys.exit(1)

	is_override_db_connection_string='false'
	db_override_jdbc_connection_string=''
	if 'is_override_db_connection_string' in globalDict:
		is_override_db_connection_string=globalDict['is_override_db_connection_string'].lower()
	if 'db_override_jdbc_connection_string' in globalDict:
		db_override_jdbc_connection_string=globalDict['db_override_jdbc_connection_string'].strip()

	if XA_DB_FLAVOR == "MYSQL":
		MYSQL_CONNECTOR_JAR=CONNECTOR_JAR
		xa_sqlObj = MysqlConf(xa_db_host, MYSQL_CONNECTOR_JAR, JAVA_BIN,db_ssl_enabled,db_ssl_required,db_ssl_verifyServerCertificate,javax_net_ssl_keyStore,javax_net_ssl_keyStorePassword,javax_net_ssl_trustStore,javax_net_ssl_trustStorePassword,db_ssl_auth_type)
		xa_db_version_file = os.path.join(RANGER_ADMIN_HOME,mysql_dbversion_catalog)
		xa_db_core_file = os.path.join(RANGER_ADMIN_HOME,mysql_core_file)
		xa_patch_file = os.path.join(RANGER_ADMIN_HOME,mysql_patches)

	elif XA_DB_FLAVOR == "ORACLE":
		ORACLE_CONNECTOR_JAR=CONNECTOR_JAR
		if xa_db_root_user.upper() == "SYS" :
			xa_db_root_user = xa_db_root_user+" AS SYSDBA"

		xa_sqlObj = OracleConf(xa_db_host, ORACLE_CONNECTOR_JAR, JAVA_BIN)
		xa_db_version_file = os.path.join(RANGER_ADMIN_HOME,oracle_dbversion_catalog)
		xa_db_core_file = os.path.join(RANGER_ADMIN_HOME,oracle_core_file)
		xa_patch_file = os.path.join(RANGER_ADMIN_HOME,oracle_patches)

	elif XA_DB_FLAVOR == "POSTGRES":
		POSTGRES_CONNECTOR_JAR=CONNECTOR_JAR
		xa_sqlObj = PostgresConf(xa_db_host, POSTGRES_CONNECTOR_JAR, JAVA_BIN,db_ssl_enabled,db_ssl_required,db_ssl_verifyServerCertificate,javax_net_ssl_keyStore,javax_net_ssl_keyStorePassword,javax_net_ssl_trustStore,javax_net_ssl_trustStorePassword,db_ssl_auth_type)
		xa_db_version_file = os.path.join(RANGER_ADMIN_HOME,postgres_dbversion_catalog)
		xa_db_core_file = os.path.join(RANGER_ADMIN_HOME,postgres_core_file)
		xa_patch_file = os.path.join(RANGER_ADMIN_HOME,postgres_patches)

	elif XA_DB_FLAVOR == "MSSQL":
		SQLSERVER_CONNECTOR_JAR=CONNECTOR_JAR
		xa_sqlObj = SqlServerConf(xa_db_host, SQLSERVER_CONNECTOR_JAR, JAVA_BIN, is_override_db_connection_string, db_override_jdbc_connection_string)
		xa_db_version_file = os.path.join(RANGER_ADMIN_HOME,sqlserver_dbversion_catalog)
		xa_db_core_file = os.path.join(RANGER_ADMIN_HOME,sqlserver_core_file)
		xa_patch_file = os.path.join(RANGER_ADMIN_HOME,sqlserver_patches)

	elif XA_DB_FLAVOR == "SQLA":
		if not os_name == "WINDOWS" :
			if os.environ['LD_LIBRARY_PATH'] == "":
				log("[E] ---------- LD_LIBRARY_PATH environment property not defined, aborting installation. ----------", "error")
				sys.exit(1)
		SQLANYWHERE_CONNECTOR_JAR=CONNECTOR_JAR
		xa_sqlObj = SqlAnywhereConf(xa_db_host, SQLANYWHERE_CONNECTOR_JAR, JAVA_BIN)
		xa_db_version_file = os.path.join(RANGER_ADMIN_HOME,sqlanywhere_dbversion_catalog)
		xa_db_core_file = os.path.join(RANGER_ADMIN_HOME,sqlanywhere_core_file)
		xa_patch_file = os.path.join(RANGER_ADMIN_HOME,sqlanywhere_patches)
	else:
		log("[E] ---------- NO SUCH SUPPORTED DB FLAVOUR.. ----------", "error")
		sys.exit(1)

	if AUDIT_DB_FLAVOR == "MYSQL":
		MYSQL_CONNECTOR_JAR=CONNECTOR_JAR
		audit_sqlObj = MysqlConf(audit_db_host,MYSQL_CONNECTOR_JAR,JAVA_BIN,db_ssl_enabled,db_ssl_required,db_ssl_verifyServerCertificate,javax_net_ssl_keyStore,javax_net_ssl_keyStorePassword,javax_net_ssl_trustStore,javax_net_ssl_trustStorePassword,db_ssl_auth_type)
		audit_db_file = os.path.join(RANGER_ADMIN_HOME,mysql_audit_file)

	elif AUDIT_DB_FLAVOR == "ORACLE":
		ORACLE_CONNECTOR_JAR=CONNECTOR_JAR
		if audit_db_root_user.upper() == "SYS":
			audit_db_root_user = audit_db_root_user+" AS SYSDBA"

		audit_sqlObj = OracleConf(audit_db_host, ORACLE_CONNECTOR_JAR, JAVA_BIN)
		audit_db_file = os.path.join(RANGER_ADMIN_HOME,oracle_audit_file)

	elif AUDIT_DB_FLAVOR == "POSTGRES":
		POSTGRES_CONNECTOR_JAR=CONNECTOR_JAR
		audit_sqlObj = PostgresConf(audit_db_host,POSTGRES_CONNECTOR_JAR,JAVA_BIN,db_ssl_enabled,db_ssl_required,db_ssl_verifyServerCertificate,javax_net_ssl_keyStore,javax_net_ssl_keyStorePassword,javax_net_ssl_trustStore,javax_net_ssl_trustStorePassword,db_ssl_auth_type)
		audit_db_file = os.path.join(RANGER_ADMIN_HOME,postgres_audit_file)

	elif AUDIT_DB_FLAVOR == "MSSQL":
		SQLSERVER_CONNECTOR_JAR=CONNECTOR_JAR
		audit_sqlObj = SqlServerConf(audit_db_host, SQLSERVER_CONNECTOR_JAR, JAVA_BIN, is_override_db_connection_string, db_override_jdbc_connection_string)
		audit_db_file = os.path.join(RANGER_ADMIN_HOME,sqlserver_audit_file)

	elif AUDIT_DB_FLAVOR == "SQLA":
		SQLANYWHERE_CONNECTOR_JAR=CONNECTOR_JAR
		audit_sqlObj = SqlAnywhereConf(audit_db_host, SQLANYWHERE_CONNECTOR_JAR, JAVA_BIN)
		audit_db_file = os.path.join(RANGER_ADMIN_HOME,sqlanywhere_audit_file)
	else:
		log("[E] ---------- NO SUCH SUPPORTED DB FLAVOUR.. ----------", "error")
		sys.exit(1)

	if not dryMode:
		log("[I] ---------- Verifying DB root password ---------- ","info")
		password_validation(xa_db_root_password,"DBA root");
		log("[I] ---------- Verifying Ranger Admin db user password ---------- ","info")
		password_validation(db_password,"admin");
	# Methods Begin
	if DBA_MODE == "TRUE" :
		if (dryMode==True):
			log("[I] Logging DBA Script in file:"+str(globalDict["dryModeOutputFile"]),"info")
			logFile("===============================================\n")
			if audit_store=="db":
				xa_sqlObj.writeDrymodeCmd(xa_db_host, audit_db_host, xa_db_root_user, xa_db_root_password, db_user, db_password, db_name, audit_db_root_user, audit_db_root_password, audit_db_user, audit_db_password, audit_db_name)
			else:
				xa_sqlObj.writeDrymodeCmd(xa_db_host, audit_db_host, xa_db_root_user, xa_db_root_password, db_user, db_password, db_name, audit_db_root_user, audit_db_root_password, db_user, db_password, db_name)
			logFile("===============================================\n")
		if (dryMode==False):
			log("[I] ---------- Creating Ranger Admin db user ---------- ","info")
			xa_sqlObj.create_rangerdb_user(xa_db_root_user, db_user, db_password, xa_db_root_password,dryMode)
			log("[I] ---------- Creating Ranger Admin database ----------","info")
			xa_sqlObj.create_db(xa_db_root_user, xa_db_root_password, db_name, db_user, db_password,dryMode)
			log("[I] ---------- Granting permission to Ranger Admin db user ----------","info")
			if not XA_DB_FLAVOR == "SQLA":
				xa_sqlObj.grant_xa_db_user(xa_db_root_user, db_name, db_user, db_password, xa_db_root_password, is_revoke,dryMode)
			# Ranger Admin DB Host AND Ranger Audit DB Host are Different OR Same
			if audit_store == "db" and audit_db_password!="":
				log("[I] ---------- Verifying Ranger Audit db user password ---------- ","info")
				password_validation(audit_db_password,"audit");
				log("[I] ---------- Verifying/Creating audit user --------- ","info")
				audit_sqlObj.create_auditdb_user(xa_db_host, audit_db_host, db_name, audit_db_name, xa_db_root_user, audit_db_root_user, db_user, audit_db_user, xa_db_root_password, audit_db_root_password, db_password, audit_db_password, DBA_MODE,dryMode)
			log("[I] ---------- Ranger Policy Manager DB and User Creation Process Completed..  ---------- ","info")
main(sys.argv)
