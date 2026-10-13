terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # State is kept locally for this single-operator capstone. For a team, switch to the S3
  # backend with native S3 locking (use_lockfile = true) so state is shared and locked.
}
