terraform {
  required_version = ">= 1.0"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "demo"
}

variable "message" {
  description = "Demo message to display"
  type        = string
  default     = "Hello from Slate Runner!"
}

variable "instance_count" {
  description = "Number of demo instances"
  type        = number
  default     = 1
}

# Null resource for demonstration
resource "null_resource" "demo" {
  count = var.instance_count

  triggers = {
    environment = var.environment
    message     = var.message
    instance    = count.index
    timestamp   = timestamp()
  }

  provisioner "local-exec" {
    command = "echo '[${var.environment}] Instance ${count.index}: ${var.message}'"
  }
}

# Random pet name generator
resource "random_pet" "server" {
  count  = var.instance_count
  length = 3
  separator = "-"
}

# Local file output
resource "local_file" "output" {
  content  = <<-EOT
    Environment: ${var.environment}
    Message: ${var.message}
    Instance Count: ${var.instance_count}
    Generated Names: ${join(", ", random_pet.server[*].id)}
    Timestamp: ${timestamp()}
  EOT
  filename = "${path.module}/output.txt"
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "message" {
  description = "Demo message"
  value       = var.message
}

output "server_names" {
  description = "Generated server names"
  value       = random_pet.server[*].id
}

output "instance_count" {
  description = "Number of instances"
  value       = var.instance_count
}
