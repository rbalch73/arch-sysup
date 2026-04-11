# Maintainer: rbalch73  <rbalch73@github.com>
pkgname=arch-sysup
pkgver=2.3.0
pkgrel=1
pkgdesc="A graphical system manager and update notifier for Arch Linux"
arch=('any')
url="https://github.com/rbalch73/arch-sysup"
license=('GPL')
depends=('python' 'tk' 'pacman-contrib' 'libnotify')
optdepends=('yay: AUR support' 'paru: AUR support')

# Points to your new v2.3 release
source=("${pkgname}-${pkgver}.tar.gz::${url}/archive/refs/tags/v${pkgver}.tar.gz")
sha256sums=('SKIP')

package() {
    # GitHub release folders are named repo_name-tag_without_v
    cd "${srcdir}/${pkgname}-${pkgver}"

    # 1. Install the main Python script
    install -Dm755 "Arch-Sysup-V2.py" "${pkgdir}/usr/share/arch-sysup/arch-sysup.py"

    # 2. Create the /usr/bin wrapper (Ensures agnostic execution)
    mkdir -p "${pkgdir}/usr/bin"
    echo -e "#!/bin/sh\npython3 /usr/share/arch-sysup/arch-sysup.py \"\$@\"" > "${pkgdir}/usr/bin/arch-sysup"
    chmod +x "${pkgdir}/usr/bin/arch-sysup"

    # 3. Install the Notifier script
    install -Dm755 "arch-sysup-notifier.py" "${pkgdir}/usr/bin/arch-sysup-notifier"

    # 4. Install the Icon
    install -Dm644 "arch-sysup.svg" "${pkgdir}/usr/share/icons/hicolor/scalable/apps/arch-sysup.svg"

    # 5. Install the Desktop Entry
    install -Dm644 "arch-sysup.desktop" "${pkgdir}/usr/share/applications/arch-sysup.desktop"

    # 6. Install the systemd User Service
    install -Dm644 "arch-sysup.service" "${pkgdir}/usr/lib/systemd/user/arch-sysup.service"
}
