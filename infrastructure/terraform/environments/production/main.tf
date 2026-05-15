terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "buildit-seo-tf-state-prod"
    key            = "infrastructure/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "buildit-seo-tf-locks-prod"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "production"
      Project     = "BuildIT SEO Operations"
      ManagedBy   = "Terraform"
    }
  }
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.5.0"

  name = "buildit-prod-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  database_subnets = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = false
  enable_dns_hostnames = true

  create_database_subnet_group = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

module "eks" {
  source = "../../modules/eks"

  cluster_name    = "buildit-prod-eks"
  cluster_version = "1.29"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  
  node_groups = {
    temporal = {
      instance_types = ["c6i.2xlarge"]
      min_size       = 3
      max_size       = 10
      desired_size   = 3
      capacity_type  = "ON_DEMAND"
    }
    api = {
      instance_types = ["m6i.xlarge"]
      min_size       = 2
      max_size       = 8
      desired_size   = 3
      capacity_type  = "ON_DEMAND"
    }
    frontend = {
      instance_types = ["t3.large"]
      min_size       = 2
      max_size       = 5
      desired_size   = 2
      capacity_type  = "ON_DEMAND"
    }
  }
}

module "rds" {
  source = "../../modules/rds"

  identifier = "buildit-prod-pg"
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.database_subnets
  
  instance_class = "db.r7g.xlarge"
  multi_az       = true
  storage_size   = 250
  
  db_name      = "seo_platform"
  db_username  = "seo_admin"
  
  allowed_security_group_ids = [module.eks.node_security_group_id]
}

module "redis" {
  source = "../../modules/redis"

  cluster_id = "buildit-prod-redis"
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  node_type           = "cache.r6g.large"
  num_cache_clusters  = 3
  
  allowed_security_group_ids = [module.eks.node_security_group_id]
}

module "msk" {
  source = "../../modules/msk"

  cluster_name = "buildit-prod-kafka"
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.private_subnets
  
  broker_node_instance_type = "kafka.m5.large"
  number_of_broker_nodes    = 3
  
  allowed_security_group_ids = [module.eks.node_security_group_id]
}
