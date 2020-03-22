#!/usr/bin/env python3
"""
Entrypoint for the CLI utility.
"""

import yaml
import boto3  # type: ignore
import structlog  # type: ignore
import kubernetes  # type: ignore
from eks_auth_sync import k8s, eks, mapping, scanner, _logging, _args


_LOG = structlog.get_logger()


def _k8s_client(session: boto3.Session, args) -> kubernetes.client.ApiClient:
    if args.auth_with_aws:
        config = eks.api_config(
            session=session, cluster=args.cluster, role_arn=args.auth_role_arn,
        )
        kubernetes.client.Configuration.set_default(config)
    elif args.in_cluster:
        kubernetes.config.load_incluster_config()
    else:
        kubernetes.config.load_kube_config()
    return kubernetes.client.ApiClient()


def main() -> None:
    """ Entrypoint for the CLI utility """
    args = _args.parser().parse_args()
    _logging.configure_logging(args)
    session = boto3.Session(region_name=args.region_name)

    scnr = scanner.Scanner(session=session, cluster=args.cluster)
    mappings = []
    if args.roles_path:
        mappings.extend(scnr.from_iam_roles(args.roles_path))
    if args.users_path:
        mappings.extend(scnr.from_iam_users(args.users_path))

    configmap = mapping.to_aws_auth(mappings)
    if args.update:
        if not mappings:
            if not args.allow_empty:
                _LOG.info("no mappings found. skipping update.")
                return
            _LOG.warning("no mapppings found. updating!")

        client = _k8s_client(session, args)
        _LOG.info("updating aws-auth configmap")
        k8s.update_aws_auth_configmap(client, configmap)
    else:
        print(yaml.dump([m.to_aws_auth_entry() for m in mappings]))


if __name__ == "__main__":
    main()
