variable "cloud_id" {
  description = "ID облака Yandex Cloud"
  type        = string
}

variable "folder_id" {
  description = "ID каталога Yandex Cloud"
  type        = string
}

variable "zone" {
  description = "Зона доступности"
  type        = string
  default     = "ru-central1-b"
}

variable "vm_name" {
  description = "Имя виртуальной машины"
  type        = string
  default     = "devops-pet-project"
}

variable "vm_cores" {
  description = "Количество ядер CPU"
  type        = number
  default     = 2
}

variable "vm_memory" {
  description = "Объем RAM в ГБ"
  type        = number
  default     = 4
}

variable "vm_core_fraction" {
  description = "Базовая производительность ядра (%)"
  type        = number
  default     = 20
}

variable "vm_disk_size" {
  description = "Размер диска в ГБ"
  type        = number
  default     = 30
}

variable "vm_preemptible" {
  description = "Прерываемая ВМ (дешевле)"
  type        = bool
  default     = true
}

variable "public_key_path" {
  description = "Путь к публичному SSH-ключу"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "v4_cidr_blocks" {
  description = "CIDR блоки для подсети"
  type        = list(string)
  default     = ["192.168.10.0/24"]
}
variable "sa_key_file" {
  description = "Path to the service account key file"
  type        = string
  default     = "/Users/rausanlapin/.authorized_key.json"
}