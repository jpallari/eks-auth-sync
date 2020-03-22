"""
CLI argument parsing
"""

import argparse


def parser() -> argparse.ArgumentParser:
    """
    Create a CLI argument parser for the app
    """
    aparser = argparse.ArgumentParser(description="Update AWS auth in EKS cluster",)
    aparser.add_argument(
        "--cluster", dest="cluster", required=True, help="Cluster to update",
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
        "--update",
        dest="update",
        action="store_true",
        help="Update cluster instead of printing the AWS auth details",
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
    aparser.add_argument(
        "--log-format",
        dest="log_format",
        default="text",
        help='Logging format. Either "json" or "text". Default: text',
    )
    aparser.add_argument(
        "--log-level",
        dest="log_level",
        default="WARNING",
        help="Logging level. Default: WARNING",
    )
    aparser.add_argument("--region-name", dest="region_name", help="AWS region to use")
    return aparser
