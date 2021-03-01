# Copyright 2020, Red Hat, Inc.
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

from __future__ import absolute_import, division, print_function
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ca_common import is_containerized, \
    exec_command, generate_ceph_cmd, exit_module
from ansible.module_utils import ceph_spec
import datetime
import json
import os
import stat
import time
import yaml


__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: ceph_mkspec

short_description: Build cephadm spec

version_added: "2.8"

description:
    - Build a cephadm compatible spec, rendering the daemon specified
options:
    cluster:
        description:
          - The ceph cluster name.
        required: false
        default: ceph
        type: str
    service_type:
        description:
          - The Ceph daemon that is going to be applied
        required: true
        type: str
        choices: ['host', 'mon', 'osd', 'mds', 'rgw']
    service_id:
        description:
          - The ID associated to the Ceph daemon
        required: false
        type: str
    service_name:
        description:
          - The name of the Ceph Daemon
        required: false
        type: str
    hosts:
        description:
          - The host list where the daemon is going to be applied
        required: false
        type: list
    host_pattern:
        description:
          - The host pattern where the daemon is going to be applied
        required: false
        type: str
    labels:
        description:
          - The list of labels used to apply the daemon on the Ceph custer
            nodes.
        required: false
        type: list
    spec:
        description:
          - The spec definition of the daemon
        type: dict
        required: false
    render_path:
        description:
          - Where the spec will be rendered
        type: str
        required: false
    apply:
        description:
          - If truem the spec rendered will be applied by the orchestrator
        type: bool
        required: false
        default: false
"""

EXAMPLES = '''
- name: create the Ceph MDS daemon spec
  ceph_spec:
    service_type: mds
    service_id: mds
    service_name: mds
    render_path: '/home/ceph-admin/specs'
    hosts:
      - host1
      - host2
      - hostN
    apply: true

- name: create the Ceph MDS daemon spec
  ceph_spec:
    service_type: mds
    service_id: mds
    service_name: mds
    host_pattern: "*mon*"
    apply: false

- name: create the Ceph MDS daemon spec
  ceph_spec:
    service_type: mds
    service_id: mds
    service_name: mds
    render_path: '/home/ceph-admin/specs'
    labels:
      - "controller"
    apply: true
'''

RETURN = '''#  '''

ALLOWED_DAEMONS = ['host', 'mon', 'mgr', 'mds', 'nfs', 'osd', 'rgw', 'grafana',
                   'crash', 'prometheus', 'alertmanager', 'node-exporter']

def generate_orch_cli(cluster, spec_path, container_image):

    args = ['apply', '--in-file', spec_path]

    cmd = generate_ceph_cmd(sub_cmd=['orch'], args=args, spec_path=spec_path, cluster=cluster, container_image=container_image)
    return cmd

def render(path, content):
    if len(content) > 0:
        if path is not None and len(path) > 0:
            with open(path, 'w') as f:
                f.write('---\n')
                f.write(yaml.dump(content, indent=2))
    else:
        print('Nothing to dump!')

def run_module():

    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=True,
        required_if=[['apply', True, ['render_path']]],
    )

    # Gather module parameters in variables
    cluster = module.params.get('cluster')
    service_type = module.params.get('service_type')
    service_id = module.params.get('service_type')
    service_name = module.params.get('service_name')
    hosts = module.params.get('hosts')
    host_pattern = module.params.get('host_pattern')
    labels = module.params.get('labels')
    spec = module.params.get('spec')
    apply = module.params.get('apply')
    render_path = module.params.get('render_path')

    if module.check_mode:
        module.exit_json(
            changed=False,
            stdout='',
            stderr='',
            rc=0,
            start='',
            end='',
            delta='',
        )

    startd = datetime.datetime.now()
    changed = False

    # PROCESSING PARAMETERS
    if service_id is None:
        service_id = service_type
    if service_name is None:
        service_name = "{}.{}".format(service_type, service_id)

    # no spec is provided
    if spec is None:
        spec = {}

    # no labels are defined
    if labels is None:
        labels = []

    d = ceph_spec.CephDaemonSpec(service_type, service_id, service_name,
            hosts,
            host_pattern,
            spec,
            labels)

    if apply:
        container_image = is_containerized()
        render('{}/{}'.format(render_path, service_type), d.make_daemon_spec())
        cmd = generate_orch_cli(cluster, '{}/{}'.format(render_path, service_type), container_image)
        rc, cmd, out, err = exec_command(module, cmd)
        # module.exit_json(changed=True, result=cmd)
        exit_module(module=module, out=out, rc=rc, cmd=cmd, err=err, startd=startd, changed=changed)
    else:
        module.exit_json(changed=True, result=d.make_daemon_spec())

def main():
    run_module()


if __name__ == '__main__':
    main()
