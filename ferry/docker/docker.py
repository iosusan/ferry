# Copyright 2014 OpenCore LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import json
import logging
import re
from subprocess import Popen, PIPE

DOCKER_SOCK='unix:////var/run/ferry.sock'

""" Docker instance """
class DockerInstance(object):
    def __init__(self, json_data=None):
        if not json_data:
            self.container = ''
            self.service_type = None
            self.host_name = None
            self.external_ip = None
            self.internal_ip = None
            self.ports = {}
            self.image = ''
            self.keys = None
            self.volumes = None
            self.default_user = None
            self.name = None
            self.args = None
        else:
            self.container = json_data['container']
            self.service_type = json_data['type']
            self.host_name = json_data['hostname']
            self.external_ip = json_data['external_ip']
            self.internal_ip = json_data['internal_ip']
            self.ports = json_data['ports']
            self.image = json_data['image']
            self.default_user = json_data['user']
            self.name = json_data['name']
            self.args = json_data['args']
            self.keys = json_data['keys']
            self.volumes = json_data['volumes']

    """
    Return in JSON format. 
    """
    def json(self):
        json_reply = { '_type' : 'docker',
                       'external_ip' : self.external_ip,
                       'internal_ip' : self.internal_ip,
                       'ports' : self.ports,
                       'hostname' : self.host_name,
                       'container' : self.container,
                       'image' : self.image,
                       'type': self.service_type, 
                       'keys' : self.keys,
                       'volumes' : self.volumes,
                       'user' : self.default_user,
                       'name' : self.name,
                       'args' : self.args }
        return json_reply


""" Alternative API for Docker that uses external commands """
class DockerCLI(object):
    def __init__(self):
        self.docker = 'docker-ferry -H=' + DOCKER_SOCK
        self.version_cmd = 'version'
        self.start_cmd = 'start'
        self.run_cmd = 'run -privileged'
        self.build_cmd = 'build -privileged'
        self.inspect_cmd = 'inspect'
        self.images_cmd = 'images'
        self.commit_cmd = 'commit'
        self.push_cmd = 'push'
        self.stop_cmd = 'stop'
        self.tag_cmd = 'tag'
        self.rm_cmd = 'rm'
        self.ps_cmd = 'ps'
        self.info_cmd = 'info'
        self.daemon = '-d'
        self.interactive = '-i'
        self.tty = '-t'
        self.port_flag = ' -p'
        self.expose_flag = ' -expose'
        self.volume_flag = ' -v'
        self.lxc_flag = ' -lxc-conf'
        self.disable_net = ' -n=false'
        self.host_flag = ' -h'
        self.fs_flag = ' -s'

    """
    Get the backend driver docker is using. 
    """
    def get_fs_type(self):
        cmd = self.docker + ' ' + self.info_cmd + ' | grep Driver | awk \'{print $2}\''
        logging.warning(cmd)

        output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()
        return output.strip()
        
    """
    Fetch the current docker version.
    """
    def version(self):
        cmd = self.docker + ' ' + self.version_cmd + ' | grep Client | awk \'{print $3}\''
        logging.warning(cmd)

        output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()
        return output.strip()
        
    """
    List all the containers. 
    """
    def list(self):
        cmd = self.docker + ' ' + self.ps_cmd + ' -q' 
        logging.warning(cmd)

        output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()
        output = output.strip()

        # There is a container ID for each line
        return output.split()

    """
    List all images that match the image name
    """
    def images(self, image_name=None):
        if not image_name:
            cmd = self.docker + ' ' + self.images_cmd + ' | awk \'{print $1}\''
            output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()
        else:
            cmd = self.docker + ' ' + self.images_cmd + ' | awk \'{print $1}\'' + ' | grep ' + image_name
            output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()

        logging.warning(cmd)
        return output.strip()
    """
    Build a new image from a Dockerfile
    """
    def build(self, image, docker_file=None):
        path = '.'
        if docker_file != None:
            path = docker_file

        cmd = self.docker + ' ' + self.build_cmd + ' -t %s %s' % (image, path)
        logging.warning(cmd)
        output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()

    def _get_default_run(self, container):
        cmd = self.docker + ' ' + self.inspect_cmd + ' ' + container.container
        logging.warning(cmd)

        output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()
        data = json.loads(output.strip())
        
        cmd = data[0]['Config']['Cmd']
        return json.dumps( {'Cmd' : cmd} )

    """
    Push an image to a remote registry.
    """
    def push(self, container, registry):
        raw_image_name = container.image.split("/")[1]
        new_image = "%s/%s" % (registry, raw_image_name)

        tag = self.docker + ' ' + self.tag_cmd + ' ' + container.image + ' ' + new_image
        push = self.docker + ' ' + self.push_cmd + ' ' + new_image
        logging.warning(tag)
        logging.warning(push)
        
        Popen(tag, stdout=PIPE, shell=True).stdout.read()
        Popen(push, stdout=PIPE, shell=True).stdout.read()

    """
    Commit a container
    """
    def commit(self, container, snapshot_name):
        default_run = self._get_default_run(container)
        run_cmd = "-run='%s'" % default_run

        # Construct a new container using the given snapshot name. 
        cmd = self.docker + ' ' + self.commit_cmd + ' ' + run_cmd + ' ' + container.container + ' ' + snapshot_name
        logging.warning(cmd)
        output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()

    """
    Stop a running container
    """
    def stop(self, container):
        cmd = self.docker + ' ' + self.stop_cmd + ' ' + container
        logging.warning(cmd)
        output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()

    """
    Remove a container
    """
    def remove(self, container):
        cmd = self.docker + ' ' + self.rm_cmd + ' ' + container
        logging.warning(cmd)
        output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()

    """
    Start a stopped container. 
    """
    def start(self, container, service_type, keys, volumes, args):
        cmd = self.docker + ' ' + self.start_cmd + ' ' + container
        logging.warning(cmd)
        output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()

        # Now parse the output to get the IP and port
        container = output.strip()
        return self.inspect(container = container, 
                            keys = keys,
                            volumes = volumes,
                            service_type = service_type, 
                            args = args)

    """
    Run a command in a virtualized container
    The Docker allocator will ignore subnet, volumes, instance_name, and key
    information since everything runs locally. 
    """
    def run(self, service_type, image, volumes, keys, open_ports, host_map=None, expose_group=None, hostname=None, default_cmd=None, args=None, lxc_opts=None):
        flags = self.daemon 

        # Specify the hostname (this is optional)
        if hostname != None:
            flags += self.host_flag
            flags += ' %s ' % hostname

        # Add the port value if provided a valid port. 
        if expose_group != None and len(expose_group) > 0:
            for p in expose_group:
                flags += self.expose_flag
                flags += ' %s' % str(p)

        # Add all the bind mounts
        if volumes != None:
            for v in volumes.keys():
                flags += self.volume_flag
                flags += ' %s:%s' % (v, volumes[v])

        # Add the key directory
        if keys != None:
            for v in keys.keys():
                flags += self.volume_flag
                # flags += ' %s:%s' % (v, keys[v])
                flags += ' %s:%s' % (keys[v], v)

        # Add the lxc options
        if lxc_opts != None:
            flags += self.disable_net
            for o in lxc_opts:
                flags += self.lxc_flag
                flags += ' \"%s\"' % o

        if not default_cmd:
            default_cmd = ''

        # Now construct the final docker command. 
        cmd = self.docker + ' ' + self.run_cmd + ' ' + flags + ' ' + image + ' ' + default_cmd
        logging.warning(cmd)
        child = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)

        err = child.stderr.read().strip()
        if re.compile('[/:\s\w]*Can\'t connect[\'\s\w]*').match(err):
            logging.error("Ferry docker daemon does not appear to be running")
            return None
        elif re.compile('Unable to find image[\'\s\w]*').match(err):
            logging.error("%s not present" % image)
            return None

        container = child.stdout.read().strip()
        return self.inspect(container, keys, volumes, hostname, open_ports, host_map, service_type, args)

    def _get_lxc_net(self, lxc_tuples):
        for l in lxc_tuples:
            if l['Key'] == 'lxc.network.ipv4':
                return l['Value']
        return None

    """
    Inspect a container and return information on how
    to connect to the container. 
    """
    def inspect(self, container, keys=None, volumes=None, hostname=None, open_ports=[], host_map=None, service_type=None, args=None):
        cmd = self.docker + ' ' + self.inspect_cmd + ' ' + container
        logging.warning(cmd)

        output = Popen(cmd, stdout=PIPE, shell=True).stdout.read()

        data = json.loads(output.strip())
        instance = DockerInstance()

        if type(data) is list:
            data = data[0]

        instance.image = data['Config']['Image']
        instance.container = data['ID']
        instance.internal_ip = data['NetworkSettings']['IPAddress']

        # If we've used the lxc config, then the networking information
        # will be located somewhere else. 
        if instance.internal_ip == "":
            instance.internal_ip = self._get_lxc_net(data['HostConfig']['LxcConf'])

        if hostname:
            instance.host_name = hostname
        else:
            # Need to inspect to get the hostname.
            instance.host_name = data['Config']['Hostname']

        instance.service_type = service_type
        instance.args = args

        if len(open_ports) == 0:
            port_mapping = data['HostConfig']['PortBindings']
            if port_mapping:
                instance.ports = port_mapping
        else:
            for p in open_ports:
                if host_map and p in host_map:
                    instance.ports[p] = host_map[p]
                else:
                    instance.ports[p] = []

        # Add any data volume information. 
        if volumes:
            instance.volumes = volumes
        else:
            instance.volumes = data['Volumes']

        if keys:
            instance.keys = keys
        return instance
