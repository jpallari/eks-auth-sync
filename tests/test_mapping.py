import unittest
import yaml
from mapping import MappingType, Mapping, to_aws_auth


class TestMappingType(unittest.TestCase):
    valid_cases = (
        ("user-to-user", MappingType.UserToUser),
        ("USER-TO-USER", MappingType.UserToUser),
        ("User-to-User", MappingType.UserToUser),
        ("role-to-user", MappingType.RoleToUser),
        ("Role-to-User", MappingType.RoleToUser),
        ("ROLE-TO-USER", MappingType.RoleToUser),
        ("role-to-node", MappingType.RoleToNode),
        ("Role-to-node", MappingType.RoleToNode),
        ("ROLE-TO-NODE", MappingType.RoleToNode),
    )

    invalid_cases = (
        "u",
        "r",
        "",
        "what",
    )

    def test_from_string_valid(self):
        for inp, out in self.valid_cases:
            self.assertEqual(MappingType.from_string(inp), out)

    def test_from_string_invalid(self):
        for inp in self.invalid_cases:
            with self.assertRaises(ValueError):
                _ = MappingType.from_string(inp)


class TestMapping(unittest.TestCase):
    aws_auth_cases = (
        (
            Mapping(
                arn="<userarn>",
                mapping_type=MappingType.UserToUser,
                username="seppo",
                groups=["frontend", "backend"],
            ),
            {
                "userarn": "<userarn>",
                "username": "seppo",
                "groups": ["frontend", "backend"],
            },
        ),
        (
            Mapping(
                arn="<rolearn>",
                mapping_type=MappingType.RoleToUser,
                username="dev",
                groups=[],
            ),
            {"rolearn": "<rolearn>", "username": "dev", "groups": [],},
        ),
        (
            Mapping(
                arn="<rolearn>",
                mapping_type=MappingType.RoleToNode,
                username="_",
                groups=[],
            ),
            {
                "rolearn": "<rolearn>",
                "username": "system:node:{{EC2PrivateDNSName}}",
                "groups": ["system:bootstrappers", "system:nodes"],
            },
        ),
    )

    def test_from_dict(self):
        inp = {
            "arn": "<userarn>",
            "mapping_type": "user-to-user",
            "username": "seppo",
            "groups": ["frontend", "backend"],
        }
        expected = Mapping(
            arn="<userarn>",
            mapping_type=MappingType.UserToUser,
            username="seppo",
            groups=["frontend", "backend"],
        )
        self.assertEqual(Mapping.from_dict(inp), expected)

    def test_aws_auth_conversion(self):
        for inp, out in self.aws_auth_cases:
            self.assertEqual(inp.to_aws_auth_entry(), out)

    def test_aws_auth_configmap(self):
        mappings = [m for m, _ in self.aws_auth_cases]
        users = [d for _, d in self.aws_auth_cases if "userarn" in d]
        roles = [d for _, d in self.aws_auth_cases if "rolearn" in d]

        cm = to_aws_auth(mappings)
        name = cm.metadata["name"]
        cmUsers = yaml.load(cm.data["mapUsers"], Loader=yaml.SafeLoader)
        cmRoles = yaml.load(cm.data["mapRoles"], Loader=yaml.SafeLoader)

        self.assertEqual(name, "aws-auth")
        self.assertEqual(cmUsers, users)
        self.assertEqual(cmRoles, roles)


if __name__ == "__main__":
    unittest.main()
