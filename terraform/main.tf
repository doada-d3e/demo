# Configure the Azure provider
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.115.0"
    }
    
    azapi = {
      source = "azure/azapi"
      version = "~> 1.14.0"
    }
  }

  required_version = ">= 1.1.0"
}

provider "azurerm" {
  features {}

}

variable "suffix" {
  description = "The suffix which should be used for all resources"
  default = "2692"
}

variable "location" {
  description = "The Azure Region in which all resources should be created."
  default = "westeurope"
}

resource "azurerm_resource_group" "main" {
  name     = "demo-app"
  location = var.location
}

resource "azurerm_user_assigned_identity" "dev" {
  location            = var.location
  name                = "dev"
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_container_registry" "main" {
  name                = "main${var.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = true
}

resource "azurerm_role_assignment" "dev_acrpull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.dev.principal_id
}

resource "azurerm_service_plan" "main" {
  name                = "plan${var.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "P0v3"
}

resource "azurerm_linux_web_app" "app" {
  name                = "app${var.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  service_plan_id     = azurerm_service_plan.main.id
  client_affinity_enabled = true
  
  app_settings = {
    "DOCKER_ENABLE_CI" = false
  }
  
  sticky_settings {
    app_setting_names = ["DOCKER_ENABLE_CI"]
  }
  
  site_config {
    always_on = false
    http2_enabled = true
  }
  
}

resource "azurerm_linux_web_app_slot" "dev" {
  app_service_id = azurerm_linux_web_app.app.id
  name                = "dev"
  client_affinity_enabled = true
  
  app_settings = {
    "WEBSITES_PORT" = 8550
    "WEBSITE_AUTH_DISABLE_IDENTITY_FLOW" = true
    "DOCKER_ENABLE_SECURITY" = false
    "DOCKER_ENABLE_CI" = true
  }
   
  identity {
    type = "UserAssigned"
    identity_ids = [ azurerm_user_assigned_identity.dev.id ]
  }
  
  site_config {

    always_on = false
    http2_enabled = true
    container_registry_use_managed_identity = true
    container_registry_managed_identity_client_id = azurerm_user_assigned_identity.dev.client_id
    application_stack {
      docker_image_name = "demo-app:latest"
      docker_registry_url = "https://${azurerm_container_registry.main.login_server}"
      docker_registry_username = azurerm_container_registry.main.admin_username
      docker_registry_password = azurerm_container_registry.main.admin_password
    }
  }
  
  logs {
    detailed_error_messages = true
    http_logs {
      file_system {
        retention_in_days = 3
        retention_in_mb = 100
      }
    }
    application_logs {
      file_system_level = "Verbose"
    }
  }
}

resource "azurerm_container_registry_webhook" "app" {
  name                = "app${var.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  registry_name       = azurerm_container_registry.main.name
  location            = var.location

  service_uri = "https://${azurerm_linux_web_app.app.site_credential[0].name}:${azurerm_linux_web_app.app.site_credential[0].password}@${azurerm_linux_web_app.app.name}.scm.azurewebsites.net/api/registry/webhook"
  actions     = ["push"]
}

output "docker" {
    value = "docker login ${azurerm_container_registry.main.login_server} --username ${azurerm_container_registry.main.admin_username} --password ${nonsensitive(azurerm_container_registry.main.admin_password)}"
}