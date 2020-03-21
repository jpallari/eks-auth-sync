import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="eks-auth-sync",
    version="0.0.1",
    description="Synchronize users to AWS EKS",
    url="https://github.com/Lepovirta/eks-auth-sync",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Jaakko Pallari",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    install_requires=[
        "boto3==1.12.5",
        "PyYAML==5.3",
        "kubernetes==10.0.1",
        "structlog==20.1.0",
    ],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["eks-auth-sync=eks_auth_sync.__main__:main"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
