# Получаем последний образ Ubuntu 22.04 LTS
data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2204-lts"
}

# Создаем сеть
resource "yandex_vpc_network" "network" {
  name = "${var.vm_name}-network"
}

# Создаем подсеть
resource "yandex_vpc_subnet" "subnet" {
  name           = "${var.vm_name}-subnet"
  zone           = var.zone
  network_id     = yandex_vpc_network.network.id
  v4_cidr_blocks = var.v4_cidr_blocks
}

# Создаем виртуальную машину
resource "yandex_compute_instance" "vm" {
  name        = var.vm_name
  platform_id = "standard-v3"
  zone        = var.zone

  resources {
    cores         = var.vm_cores
    memory        = var.vm_memory
    core_fraction = var.vm_core_fraction  # Для экономии средств
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.image_id
      size     = var.vm_disk_size
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.subnet.id
    nat       = true  # Публичный IP
  }

  metadata = {
    ssh-keys = "ubuntu:${file(var.public_key_path)}"
    serial-port-enable = "1"
  }

  scheduling_policy {
    preemptible = var.vm_preemptible  # Прерываемая ВМ для экономии
  }

  allow_stopping_for_update = true
}

# Выводим информацию о созданной ВМ
output "vm_ip" {
  description = "Публичный IP адрес ВМ"
  value       = yandex_compute_instance.vm.network_interface.0.nat_ip_address
}

output "vm_fqdn" {
  description = "FQDN виртуальной машины"
  value       = yandex_compute_instance.vm.fqdn
}