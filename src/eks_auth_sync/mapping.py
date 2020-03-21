"""
Mapping describes a common mapping format from IAM users and roles to Kubernetes users.
"""
import typing
import enum
import yaml
from kubernetes.client import V1ConfigMap  # type: ignore

NODE_USERNAME = "system:node:{{EC2PrivateDNSName}}"
NODE_GROUPS = ("system:bootstrappers", "system:nodes")


class MappingType(enum.Enum):
    """
    Describes the mapping from AWS IAM user or role to a user in Kubernetes.

    * UserToUser: IAM user to a normal user in Kubernetes
    * RoleToUser: IAM role to a normal user in Kubernetes
    * RoleToNode: IAM role to a node user in Kubernetes
    """

    UserToUser = "user-to-user"
    RoleToUser = "role-to-user"
    RoleToNode = "role-to-node"

    @classmethod
    def from_string(
        cls: typing.Type["MappingType"], mapping_type_str: str
    ) -> "MappingType":
        """
        Converts the given string to a mapping type.

        :param mapping_type_str: A string matching one of the mapping types
        :returns: A mapping type corresponding to the string.

        Throws ValueError when the string doesn't match any of the mapping types.
        See the mapping type values for the expected string representations.
        """
        mapping_type_str = mapping_type_str.lower()
        mapping_types: typing.List["MappingType"] = list(cls)
        for mapping_type in mapping_types:
            if mapping_type_str == mapping_type.value:
                return mapping_type
        raise ValueError(f"Invalid IAM type: {mapping_type_str}")


class Mapping(typing.NamedTuple):
    """
    Mapping describes a common mapping format from IAM users and roles to Kubernetes users.

    :param arn: IAM user/role ARN string
    :param mapping_type: Describes the mapping from AWS IAM user or role to a user in Kubernetes.
    :param username: Kubernetes username for the IAM user/role
    :param groups: A list of groups for the Kubernetes user
    """

    arn: str
    mapping_type: MappingType
    username: str
    groups: typing.List[str]

    @classmethod
    def from_dict(cls, dictionary: dict) -> "Mapping":
        """
        Reads mapping contents from a dictionary.

        :param dictionary: The dictionary containing the mapping information.
        :returns: A mapping based on the dictionary contents

        The dictionary should have the following entries:
        * `arn`: IAM user/role ARN string
        * `mapping_type`: A mapping type in string format.
           See `MappingType#from_string` for more information.
        * `username`: Kubernetes username in string format
        * `groups`: A list of groups for the Kubernetes user
        """
        return cls(
            arn=dictionary["arn"],
            mapping_type=MappingType.from_string(dictionary["mapping_type"]),
            username=dictionary["username"],
            groups=dictionary["groups"],
        )

    @property
    def is_iam_user_mapping(self) -> bool:
        """ Returns `True` if the mapping is for an IAM user """
        return self.mapping_type == MappingType.UserToUser

    @property
    def is_iam_role_mapping(self) -> bool:
        """ Returns `True` if the mapping is for an IAM role """
        return self.mapping_type in (MappingType.RoleToNode, MappingType.RoleToUser)

    def to_aws_auth_entry(self) -> dict:
        """
        Converts the mapping to a AWS auth entry.

        :returns: Mapping as an AWS auth entry in dictionary format.
        """
        if self.mapping_type == MappingType.UserToUser:
            return {
                "userarn": self.arn,
                "username": self.username,
                "groups": self.groups,
            }
        if self.mapping_type == MappingType.RoleToUser:
            return {
                "rolearn": self.arn,
                "username": self.username,
                "groups": self.groups,
            }
        if self.mapping_type == MappingType.RoleToNode:
            return {
                "rolearn": self.arn,
                "username": NODE_USERNAME,
                "groups": list(NODE_GROUPS),
            }
        raise NotImplementedError("Unexpected condition")


def to_aws_auth(mappings: typing.List[Mapping]) -> V1ConfigMap:
    """
    Converts the given list of mappings to a AWS auth ConfigMap.

    :param mappings: list of mappings
    :returns: a ConfigMap containing the mappings in AWS auth format.
    """
    return V1ConfigMap(
        metadata={"name": "aws-auth"},
        data={
            "mapUsers": yaml.dump(
                [m.to_aws_auth_entry() for m in mappings if m.is_iam_user_mapping]
            ),
            "mapRoles": yaml.dump(
                [m.to_aws_auth_entry() for m in mappings if m.is_iam_role_mapping]
            ),
        },
    )
