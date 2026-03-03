terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
  required_version = ">= 0.13"
}

provider "yandex" {
  service_account_key_file = var.sa_key_file
  folder_id                = var.folder_id
  cloud_id                 = var.cloud_id
  zone                     = var.zone
}