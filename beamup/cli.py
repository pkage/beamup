import os
from pathlib import Path
from typing import Any, Dict

import asyncclick as click
import boto3.session
from botocore.config import Config
from humanize import naturalsize
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
import toml

from . import console, pprint


def get_config_path() -> Path:
    local_path = Path('./beam_config.toml')
    if local_path.exists():
        return local_path

    system_path = Path('~/.config/beamup/beam_config.toml').expanduser()
    if system_path.exists():
        return system_path

    
    raise FileNotFoundError('no suitable config found!')


def load_config(config_path):
    with open(config_path, 'r') as fp:
        config = toml.load(fp)

    return config


def load_profile(config, profile='default'):
    if not 'profile' in config:
        raise ValueError('No profiles in config!')

    if not profile in config['profile']:
        raise ValueError(f'No such profile \'{profile}\'')
    
    return config['profile'][profile]


def create_s3_client(profile: Dict):
    session = boto3.session.Session()

    s3_client = session.client(
        's3',
        region_name=profile['region'],
        endpoint_url=profile['endpoint'],
        aws_access_key_id=profile['access_key'],
        aws_secret_access_key=profile['secret_key'],
        config=Config(s3={'addressing_style': 'virtual'})
    )

    return s3_client


async def upload_asset(filename: Path, bucket: str, key: str, s3_client: Any, private=False):
    filesize = filename.stat().st_size

    with Progress(
        # TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        TransferSpeedColumn()
    ) as progress:
        upload_task = progress.add_task("Uploading...", total=filesize)
        
        s3_client.upload_file(
            Filename=filename,
            Bucket=bucket,
            Key=key,
            Callback=lambda bytes_transferred: progress.update(upload_task, advance=bytes_transferred),
            ExtraArgs={
                'ACL': 'private' if private else 'public-read'
            }
        )


def compute_key(profile, requested_key, filename):
    key = os.path.join(
        profile['prefix'],
        requested_key,
        filename
    )

    return key


def compute_final_url(profile, key):
    access_url = profile['access_url']
    return os.path.join(access_url, key)


@click.command()
@click.argument('filename', type=click.Path(exists=True))
@click.option('-k', '--key', type=str, default='', help='Key to upload to')
@click.option('-p', '--private', is_flag=True, help='Upload with a private ACL')
@click.option('-d', '--dry-run', is_flag=True, help='Dry run only')
async def cli_entrypoint(filename: str, key: str, private: bool = False, dry_run: bool = False):
    target_file = Path(filename)
    config_path = get_config_path()
    config = load_config(config_path)
    profile = load_profile(config)

    filesize = target_file.stat().st_size

    key = compute_key(profile, key, target_file)

    console.print(f'Uploading [cyan]{target_file}[/] to [cyan]{key}[/] ({naturalsize(filesize, binary=True)}).')

    if dry_run:
        return

    s3_client = create_s3_client(profile)
    await upload_asset(
        target_file,
        profile['bucket'],
        key,
        s3_client,
        private=private
    )


    if not private:
        url = compute_final_url(profile, key)
        console.print(f'Uploaded to [cyan]{url}')
    else:
        console.print(f'Upload finished (private ACL).')


    # response = s3_client.list_objects_v2(
    #     Bucket=profile['bucket'],
    #     Prefix=profile['prefix'],
    #     MaxKeys=100
    # )

    # pprint(response)
