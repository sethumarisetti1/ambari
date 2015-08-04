"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import collections
import re

import ambari_simplejson as json # simplejson is much faster comparing to Python 2.6 json module and has the same functions set.

from resource_management.libraries.script import Script
from resource_management.libraries.functions import default
from resource_management.libraries.functions import format
from resource_management.libraries.functions import conf_select
from resource_management.libraries.functions import hdp_select
from resource_management.libraries.functions import format_jvm_option
from resource_management.libraries.functions.version import format_hdp_stack_version
from resource_management.libraries.functions.version import compare_versions
from ambari_commons.os_check import OSCheck


config = Script.get_config()
tmp_dir = Script.get_tmp_dir()

artifact_dir = format("{tmp_dir}/AMBARI-artifacts/")
jce_policy_zip = default("/hostLevelParams/jce_name", None) # None when jdk is already installed by user
jce_location = config['hostLevelParams']['jdk_location']
jdk_name = default("/hostLevelParams/jdk_name", None)
java_home = config['hostLevelParams']['java_home']
java_version = int(config['hostLevelParams']['java_version'])

ambari_server_hostname = config['clusterHostInfo']['ambari_server_host'][0]

stack_version_unformatted = str(config['hostLevelParams']['stack_version'])
hdp_stack_version = format_hdp_stack_version(stack_version_unformatted)

security_enabled = config['configurations']['cluster-env']['security_enabled']
hdfs_user = config['configurations']['hadoop-env']['hdfs_user']

# Some datanode settings
dfs_dn_addr = default('/configurations/hdfs-site/dfs.datanode.address', None)
dfs_dn_http_addr = default('/configurations/hdfs-site/dfs.datanode.http.address', None)
dfs_dn_https_addr = default('/configurations/hdfs-site/dfs.datanode.https.address', None)
dfs_http_policy = default('/configurations/hdfs-site/dfs.http.policy', None)
secure_dn_ports_are_in_use = False

def get_port(address):
  """
  Extracts port from the address like 0.0.0.0:1019
  """
  if address is None:
    return None
  m = re.search(r'(?:http(?:s)?://)?([\w\d.]*):(\d{1,5})', address)
  if m is not None:
    return int(m.group(2))
  else:
    return None

def is_secure_port(port):
  """
  Returns True if port is root-owned at *nix systems
  """
  if port is not None:
    return port < 1024
  else:
    return False

# hadoop default params
mapreduce_libs_path = "/usr/lib/hadoop-mapreduce/*"

# upgrades would cause these directories to have a version instead of "current"
# which would cause a lot of problems when writing out hadoop-env.sh; instead
# force the use of "current" in the hook
hadoop_home = hdp_select.get_hadoop_dir("home", force_latest_on_upgrade=True)
hadoop_libexec_dir = hdp_select.get_hadoop_dir("libexec", force_latest_on_upgrade=True)

hadoop_conf_empty_dir = "/etc/hadoop/conf.empty"
hadoop_secure_dn_user = hdfs_user
hadoop_dir = "/etc/hadoop"
versioned_hdp_root = '/usr/hdp/current'

# HDP 2.2+ params
if Script.is_hdp_stack_greater_or_equal("2.2"):
  mapreduce_libs_path = "/usr/hdp/current/hadoop-mapreduce-client/*"

  # not supported in HDP 2.2+
  hadoop_conf_empty_dir = None

  if not security_enabled:
    hadoop_secure_dn_user = '""'
  else:
    dfs_dn_port = get_port(dfs_dn_addr)
    dfs_dn_http_port = get_port(dfs_dn_http_addr)
    dfs_dn_https_port = get_port(dfs_dn_https_addr)
    # We try to avoid inability to start datanode as a plain user due to usage of root-owned ports
    if dfs_http_policy == "HTTPS_ONLY":
      secure_dn_ports_are_in_use = is_secure_port(dfs_dn_port) or is_secure_port(dfs_dn_https_port)
    elif dfs_http_policy == "HTTP_AND_HTTPS":
      secure_dn_ports_are_in_use = is_secure_port(dfs_dn_port) or is_secure_port(dfs_dn_http_port) or is_secure_port(dfs_dn_https_port)
    else:   # params.dfs_http_policy == "HTTP_ONLY" or not defined:
      secure_dn_ports_are_in_use = is_secure_port(dfs_dn_port) or is_secure_port(dfs_dn_http_port)
    if secure_dn_ports_are_in_use:
      hadoop_secure_dn_user = hdfs_user
    else:
      hadoop_secure_dn_user = '""'

#hadoop params
hdfs_log_dir_prefix = config['configurations']['hadoop-env']['hdfs_log_dir_prefix']
hadoop_pid_dir_prefix = config['configurations']['hadoop-env']['hadoop_pid_dir_prefix']
hadoop_root_logger = config['configurations']['hadoop-env']['hadoop_root_logger']

if hdp_stack_version != "" and compare_versions(hdp_stack_version, '2.0') >= 0 and compare_versions(hdp_stack_version, '2.1') < 0 and not OSCheck.is_suse_family():
  # deprecated rhel jsvc_path
  jsvc_path = "/usr/libexec/bigtop-utils"
else:
  jsvc_path = "/usr/lib/bigtop-utils"

hadoop_heapsize = config['configurations']['hadoop-env']['hadoop_heapsize']
namenode_heapsize = config['configurations']['hadoop-env']['namenode_heapsize']
namenode_opt_newsize = config['configurations']['hadoop-env']['namenode_opt_newsize']
namenode_opt_maxnewsize = config['configurations']['hadoop-env']['namenode_opt_maxnewsize']
namenode_opt_permsize = format_jvm_option("/configurations/hadoop-env/namenode_opt_permsize","128m")
namenode_opt_maxpermsize = format_jvm_option("/configurations/hadoop-env/namenode_opt_maxpermsize","256m")

jtnode_opt_newsize = "200m"
jtnode_opt_maxnewsize = "200m"
jtnode_heapsize =  "1024m"
ttnode_heapsize = "1024m"

dtnode_heapsize = config['configurations']['hadoop-env']['dtnode_heapsize']
nfsgateway_heapsize = config['configurations']['hadoop-env']['nfsgateway_heapsize']
mapred_pid_dir_prefix = default("/configurations/mapred-env/mapred_pid_dir_prefix","/var/run/hadoop-mapreduce")
mapred_log_dir_prefix = default("/configurations/mapred-env/mapred_log_dir_prefix","/var/log/hadoop-mapreduce")
hadoop_env_sh_template = config['configurations']['hadoop-env']['content']

#users and groups
hbase_user = config['configurations']['hbase-env']['hbase_user']
smoke_user =  config['configurations']['cluster-env']['smokeuser']
gmetad_user = config['configurations']['ganglia-env']["gmetad_user"]
gmond_user = config['configurations']['ganglia-env']["gmond_user"]
tez_user = config['configurations']['tez-env']["tez_user"]
oozie_user = config['configurations']['oozie-env']["oozie_user"]
falcon_user = config['configurations']['falcon-env']["falcon_user"]
ranger_user = config['configurations']['ranger-env']["ranger_user"]

user_group = config['configurations']['cluster-env']['user_group']

ganglia_server_hosts = default("/clusterHostInfo/ganglia_server_host", [])
namenode_host = default("/clusterHostInfo/namenode_host", [])
hbase_master_hosts = default("/clusterHostInfo/hbase_master_hosts", [])
oozie_servers = default("/clusterHostInfo/oozie_server", [])
falcon_server_hosts = default("/clusterHostInfo/falcon_server_hosts", [])
ranger_admin_hosts = default("/clusterHostInfo/ranger_admin_hosts", [])

has_namenode = not len(namenode_host) == 0
has_ganglia_server = not len(ganglia_server_hosts) == 0
has_tez = 'tez-site' in config['configurations']
has_hbase_masters = not len(hbase_master_hosts) == 0
has_oozie_server = not len(oozie_servers) == 0
has_falcon_server_hosts = not len(falcon_server_hosts) == 0
has_ranger_admin = not len(ranger_admin_hosts) == 0

if has_namenode:
  hadoop_conf_dir = conf_select.get_hadoop_conf_dir(force_latest_on_upgrade=True)

hbase_tmp_dir = "/tmp/hbase-hbase"

proxyuser_group = default("/configurations/hadoop-env/proxyuser_group","users")
ranger_group = config['configurations']['ranger-env']['ranger_group']
dfs_cluster_administrators_group = config['configurations']['hdfs-site']["dfs.cluster.administrators"]

ignore_groupsusers_create = default("/configurations/cluster-env/ignore_groupsusers_create", False)

smoke_user_dirs = format("/tmp/hadoop-{smoke_user},/tmp/hsperfdata_{smoke_user},/home/{smoke_user},/tmp/{smoke_user},/tmp/sqoop-{smoke_user}")
if has_hbase_masters:
  hbase_user_dirs = format("/home/{hbase_user},/tmp/{hbase_user},/usr/bin/{hbase_user},/var/log/{hbase_user},{hbase_tmp_dir}")
#repo params
repo_info = config['hostLevelParams']['repo_info']
service_repo_info = default("/hostLevelParams/service_repo_info",None)

user_to_groups_dict = collections.defaultdict(lambda:[user_group])
user_to_groups_dict[smoke_user] = [proxyuser_group]
if has_ganglia_server:
  user_to_groups_dict[gmond_user] = [gmond_user]
  user_to_groups_dict[gmetad_user] = [gmetad_user]
if has_tez:
  user_to_groups_dict[tez_user] = [proxyuser_group]
if has_oozie_server:
  user_to_groups_dict[oozie_user] = [proxyuser_group]
if has_falcon_server_hosts:
  user_to_groups_dict[falcon_user] = [proxyuser_group]
if has_ranger_admin:
  user_to_groups_dict[ranger_user] = [ranger_group]

user_to_gid_dict = collections.defaultdict(lambda:user_group)

user_list = json.loads(config['hostLevelParams']['user_list'])
group_list = json.loads(config['hostLevelParams']['group_list'])
host_sys_prepped = default("/hostLevelParams/host_sys_prepped", False)

tez_am_view_acls = config['configurations']['tez-site']["tez.am.view-acls"]
override_hbase_uid = config['configurations']['hbase-env']["override_hbase_uid"]
