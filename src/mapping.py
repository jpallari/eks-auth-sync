import typing
import enum
import yaml
from kubernetes.client import V1ConfigMap # type: ignore

NODE_USERNAME = "system:node:{{EC2PrivateDNSName}}"
NODE_GROUPS = ("system:bootstrappers", "system:nodes")


class MappingType(enum.Enum):
    UserToUser = "user-to-user"
    RoleToUser = "role-to-user"
    RoleToNode = "role-to-node"

    @classmethod
    def from_string(cls: typing.Type["MappingType"], s: str) -> "MappingType":
        s = s.lower()
        mts: typing.List["MappingType"] = list(cls)
        for mt in mts:
            if s == mt.value:
                return mt
        raise ValueError(f"Invalid IAM type: {s}")


class Mapping(typing.NamedTuple):
    arn: str
    mapping_type: MappingType
    username: str
    groups: typing.List[str]

    @classmethod
    def from_dict(cls, d: dict) -> "Mapping":
        return cls(
            arn=d["arn"],
            mapping_type=MappingType.from_string(d["mapping_type"]),
            username=d["username"],
            groups=d["groups"],
        )

    @property
    def is_iam_user_mapping(self) -> bool:
        return self.mapping_type == MappingType.UserToUser

    @property
    def is_iam_role_mapping(self) -> bool:
        return self.mapping_type in (MappingType.RoleToNode, MappingType.RoleToUser)

    def to_aws_auth_entry(self) -> dict:
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
