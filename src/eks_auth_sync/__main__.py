#!/usr/bin/env python3
"""
Entrypoint for the CLI utility.
"""

import argparse
import yaml
import boto3  # type: ignore
import structlog  # type: ignore
import kubernetes  # type: ignore
from eks_auth_sync import k8s, eks, mapping, scanner


_LOG = structlog.get_logger()


def _argparser() -> argparse.ArgumentParser:
    aparser = argparse.ArgumentParser(description="Update AWS auth in EKS cluster",)
    aparser.add_argument(
        "--cluster", dest="cluster", required=True, help="Cluster to update",
    )
    aparser.add_argument(
        "--update",
        dest="update",
        action="store_true",
        help="Update cluster instead of printing the AWS auth details",
    )
    aparser.add_argument(
        "--log-format",
        dest="log_format",
        default="text",
        help='Logging format. Either "json" or "text". Default: text',
    )
    aparser.add_argument(
        "--scan-roles-path",
        dest="roles_path",
        help="AWS IAM role path to scan for EKS users",
    )
    aparser.add_argument(
        "--scan-users-path",
        dest="users_path",
        help="AWS IAM user path to scan for EKS users",
    )
    aparser.add_argument(
        "--allow-empty",
        dest="allow_empty",
        action="store_true",
        help="If enabled, AWS auth is updated even when no mappings are found.",
    )
    aparser.add_argument(
        "--in-cluster",
        dest="in_cluster",
        action="store_true",
        help="If enabled, in-cluster configuration is used for accessing EKS.",
    )
    aparser.add_argument(
        "--auth-with-aws",
        dest="auth_with_aws",
        action="store_true",
        help="If enabled, AWS APIs are used directly to access EKS",
    )
    aparser.add_argument(
        "--auth-role-arn",
        dest="auth_role_arn",
        help="Role to assume for EKS authentication",
    )
    aparser.add_argument("--region-name", dest="region_name", help="AWS region to use")
    return aparser


def _configure_logging(args) -> None:
    processors = [
        structlog.processors.TimeStamper(),
    ]
    if args.log_format.lower() == "json":
        processors.extend([structlog.processors.JSONRenderer()])
    elif args.log_format.lower() == "text":
        processors.extend(
            [
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.format_exc_info,
                structlog.dev.ConsoleRenderer(),
            ]
        )
    else:
        raise ValueError("Invalid log format: %s" % args.log_format)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    _LOG.bind(cluster=args.cluster)


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
    args = _argparser().parse_args()
    _configure_logging(args)
    session = boto3.Session(region_name=args.region_name)

    scnr = scanner.Scanner(session=session, cluster=args.cluster)
    mappings = []
    if args.roles_path:
        mappings.extend(scnr.from_iam_roles(args.roles_path))
    if args.users_path:
        mappings.extend(scnr.from_iam_users(args.users_path))

    configmap = mapping.to_aws_auth(mappings)
    if args.update:
        if not mappings and not args.allow_empty:
            _LOG.info("no mappings found. skipping update.")
            return
        client = _k8s_client(session, args)
        _LOG.info("updating aws-auth configmap")
        k8s.update_aws_auth_configmap(client, configmap)
    else:
        print(yaml.dump([m.to_aws_auth_entry() for m in mappings]))


if __name__ == "__main__":
    main()
