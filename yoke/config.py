import boto3
import json
import logging
import os
import ruamel.yaml as yaml

import utils

LOG = logging.getLogger(__name__)
LAMBDA_ROLE_ARN_TEMPLATE = "arn:aws:iam::{account_id}:role/{role}"


class YokeConfig(object):

    def __init__(self, project_dir, stage):
        self.project_dir = project_dir
        self.stage = stage

    def get_config(self):
        LOG.warning("Getting config from %s ...", self.project_dir)
        yoke_path = os.path.join(self.project_dir, 'yoke.yml')
        with open(yoke_path, 'r') as config_file:
            raw = config_file.read()
        config = yaml.load(raw)
        stage = self.get_stage(self.stage, config)

        # Set provided stage's config to default configs
        if stage == 'default':
            config['stages'][self.stage] = config['stages'][stage]
            stage = self.stage
        config['stage'] = self.stage

        config['project_dir'] = self.project_dir
        config['account_id'] = self.get_account_id()

        if config['stages'][self.stage].get('secret_config'):
            dec_config = utils.decrypt(config)
            config['stages'][self.stage]['config'].update(dec_config)

        # Set proper Lambda ARN for role
        config['Lambda']['config']['role'] = LAMBDA_ROLE_ARN_TEMPLATE.format(
            account_id=config['account_id'],
            role=config['Lambda']['config']['role']
        )

        LOG.info('Config:\n%s', json.dumps(config, indent=4))

        return config

    def get_stage(self, stage, config):
        assert stage, "No YOKE_STAGE envvar found - aborting!"
        LOG.warning("Loading stage %s ...", stage)
        if not config['stages'].get(stage):
            if not config['stages'].get('default'):
                LOG.warning('%s stage was not found and no default '
                            'stage was provided - aborting!', stage)
                raise
            LOG.warning("%s stage was not found - using default ...", stage)
            stage = 'default'
        return stage

    def get_account_id(self):
        LOG.warning('Getting AWS Account Credentials ...')
        aws_account_id = boto3.client('iam').list_users(MaxItems=1)[
            'Users'][0]['Arn'].split(':')[4]
        return str(aws_account_id)
