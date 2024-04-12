# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: License :: OSI Approved :: MIT No Attribution License (MIT-0)
import setuptools

try:
    with open("README.md") as fp:
        long_description = fp.read()
except IOError as e:
    long_description = ''

setuptools.setup(
    name="emr-roadshow",
    version="3.0.0",

    description="A CDK Python app for Spark Structured Streaming ETL",
    long_description=long_description,
    long_description_content_type="text/markdown",
    
    author="meloyang",

    package_dir={"": "source"},
    packages=setuptools.find_packages(where="source"),

    install_requires=[
        "aws-cdk-lib==2.105.0",
        "aws-cdk.aws-msk-alpha==2.105.0a0",
        "aws-cdk.lambda-layer-kubectl-v26",
        "constructs>=10.0.0,<11.0.0",
        "pyyaml==6.0.1"
    ],

    python_requires=">=3.7",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: MIT License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
