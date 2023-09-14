%global _gitcommit_engine 5d6db84
%global _gitcommit_cli 297e128
%global _source_engine moby-%{version}
%global _source_client cli-%{version}
%global _source_docker_init tini-0.19.0
%define _debugsource_template %{nil}

Name: 	  moby
Version:  20.10.24
Release:  4
Summary:  The open-source application container engine
License:  ASL 2.0
URL:	  https://www.docker.com
# https://github.com/docker/cli/archive/refs/tags/v20.10.24.tar.gz
Source0:  cli-%{version}.tar.gz
# https://github.com/moby/moby/archive/refs/tags/v20.10.24.tar.gz
Source1:  moby-%{version}.tar.gz
# https://github.com/krallin/tini/archive/refs/tags/v0.19.0.tar.gz
Source2:  tini-0.19.0.tar.gz
Source3:  docker.service
Source4:  docker.socket
Source5:  docker.sysconfig
Source6:  apply-patches
Source7:  series.conf
Source8:  patch.tar.gz


Requires: %{name}-engine = %{version}-%{release}
Requires: %{name}-client = %{version}-%{release}

# conflicting packages
Conflicts: docker-ce
Conflicts: docker-io
Conflicts: docker-engine
Conflicts: docker-engine-cs
Conflicts: docker-ee

%description
Docker is a product for you to build, ship and run any application as a
lightweight container.

%package engine
Summary: Docker daemon binary and related utilities

Requires: /usr/sbin/groupadd
Requires: %{name}-client = %{version}-%{release}
Requires: docker-runc
Requires: container-selinux >= 2:2.74
Requires: libseccomp >= 2.3
Requires: systemd
Requires: iptables
Requires: libcgroup
Requires: containerd
Requires: tar
Requires: xz

BuildRequires: bash
BuildRequires: ca-certificates
BuildRequires: cmake
BuildRequires: device-mapper-devel
BuildRequires: gcc
BuildRequires: git
BuildRequires: glibc-static
BuildRequires: libarchive
BuildRequires: libseccomp-devel
BuildRequires: libselinux-devel
BuildRequires: libtool
BuildRequires: libtool-ltdl-devel
BuildRequires: make
BuildRequires: pkgconfig
BuildRequires: pkgconfig(systemd)
BuildRequires: selinux-policy-devel
BuildRequires: systemd-devel
BuildRequires: tar
BuildRequires: which
BuildRequires: golang  >= 1.18.0
BuildRequires: docker-proxy

%description engine
Docker daemon binary and related utilities

%package client
Summary: Docker client binary and related utilities

Requires: /bin/sh
Requires: %{name}-engine = %{version}-%{release}
BuildRequires: libtool-ltdl-devel

%description client
Docker client binary and related utilities

%prep
%setup -q -n %{_source_client}
%setup -q -T -n %{_source_engine} -b 1
%setup -q -T -n %{_source_docker_init} -b 2

cd %{_builddir}
cp %{SOURCE6} .
cp %{SOURCE7} .
cp %{SOURCE8} .

sh ./apply-patches

%build
export GO111MODULE=off
# build docker daemon
export DOCKER_GITCOMMIT=%{_gitcommit_engine}
export DOCKER_BUILDTAGS="exclude_graphdriver_btrfs"

pushd %{_builddir}/%{_source_engine}
AUTO_GOPATH=1 VERSION=%{version} PRODUCT=docker hack/make.sh dynbinary
popd

# build docker-tini
pushd %{_builddir}/%{_source_docker_init}
cmake .
make tini-static
popd

# build cli
pushd %{_builddir}/%{_source_client}
mkdir -p .gopath/src/github.com/docker/cli
export GOPATH=`pwd`/.gopath
rm -rf .gopath/src/github.com/docker/cli
ln -s %{_builddir}/%{_source_client} .gopath/src/github.com/docker/cli
pushd .gopath/src/github.com/docker/cli
DISABLE_WARN_OUTSIDE_CONTAINER=1 make VERSION=%{version} GITCOMMIT=%{_gitcommit_cli} dynbinary
popd
popd

%check
# check for daemon
ver="$(%{_builddir}/%{_source_engine}/bundles/dynbinary-daemon/dockerd --version)"; \
    test "$ver" = "Docker version %{version}, build %{_gitcommit_engine}" && echo "PASS: daemon version OK" || (echo "FAIL: daemon version ($ver) did not match" && exit 1)
# check for client
ver="$(%{_builddir}/%{_source_client}/build/docker --version)"; \
    test "$ver" = "Docker version %{version}, build %{_gitcommit_cli}" && echo "PASS: cli version OK" || (echo "FAIL: cli version ($ver) did not match" && exit 1)


%install
# install daemon binary
install -D -p -m 0755 $(readlink -f %{_builddir}/%{_source_engine}/bundles/dynbinary-daemon/dockerd) %{buildroot}%{_bindir}/dockerd

# install proxy
install -D -p -m 0755 /usr/bin/docker-proxy %{buildroot}%{_bindir}/docker-proxy

# install tini
install -D -p -m 755 %{_builddir}/%{_source_docker_init}/tini-static %{buildroot}%{_bindir}/docker-init

# install systemd scripts
install -D -m 0644 %{SOURCE3} %{buildroot}%{_unitdir}/docker.service
install -D -m 0644 %{SOURCE4} %{buildroot}%{_unitdir}/docker.socket

# for additional args
install -Dpm 644 %{SOURCE5} %{buildroot}%{_sysconfdir}/sysconfig/docker

# install docker client
install -p -m 0755 $(readlink -f %{_builddir}/%{_source_client}/build/docker) %{buildroot}%{_bindir}/docker

# add bash, zsh, and fish completions
install -d %{buildroot}%{_datadir}/bash-completion/completions
install -d %{buildroot}%{_datadir}/zsh/vendor-completions
install -d %{buildroot}%{_datadir}/fish/vendor_completions.d
install -p -m 644 %{_builddir}/%{_source_client}/contrib/completion/bash/docker %{buildroot}%{_datadir}/bash-completion/completions/docker
install -p -m 644 %{_builddir}/%{_source_client}/contrib/completion/zsh/_docker %{buildroot}%{_datadir}/zsh/vendor-completions/_docker
install -p -m 644 %{_builddir}/%{_source_client}/contrib/completion/fish/docker.fish %{buildroot}%{_datadir}/fish/vendor_completions.d/docker.fish

# add docs
install -d %{buildroot}%{_pkgdocdir}
install -p -m 644 %{_builddir}/%{_source_client}/{LICENSE,MAINTAINERS,NOTICE,README.md} %{buildroot}%{_pkgdocdir}

%files
# empty as it depends on engine and client

%files engine
%config(noreplace) %{_sysconfdir}/sysconfig/docker
%{_bindir}/dockerd
%{_bindir}/docker-proxy
%{_bindir}/docker-init
%{_unitdir}/docker.service
%{_unitdir}/docker.socket

%files client
%{_bindir}/docker
%{_datadir}/bash-completion/completions/docker
%{_datadir}/zsh/vendor-completions/_docker
%{_datadir}/fish/vendor_completions.d/docker.fish
%doc %{_pkgdocdir}

%post
%systemd_post docker.service
if ! getent group docker > /dev/null; then
    groupadd --system docker
fi

%preun
%systemd_preun docker.service docker.socket

%postun
%systemd_postun_with_restart docker.service

%changelog
* Thu Sep 14 2023 xulei<xulei@xfusion.com> - 20.10.24-4
- DESC: Fix missing runc dependencies
        The declaration conflicts with the installation of docker-engine

* Mon Sep 4 2023 xulei<xulei@xfusion.com> - 20.10.24-3
- Fix the conflict libnetwork installation

* Sun Jul 16 2023 xulei<xulei@xfusion.com> - 20.10.24-2
- DESC: fix non-blocking awslogs log drop bug
        fix panic if mount is not a volume

* Mon Apr 10 2023 xulei<xulei@xfusion.com> - 20.10.24-1
- DESC: update to 20.10.24

* Tue Apr 4 2023 zhangzhihui<zhangzhihui@xfusion.com> - 20.10.23-3
- DESC: sync upstream patch
        Dockerfile: configure code dir as "safe" directory

* Fri Mar 31 2023 zhangzhihui<zhangzhihui@xfusion.com> - 20.10.23-2
- DESC: sync upstream patch to update containerd to v1.6.16

* Wed Mar 29 2023 xulei<xulei@xfusion.com> - 20.10.23-1
- DESC:update to 20.10.23

* Wed Mar 8 2023 xulei<xulei@xfusion.com> - 20.10.21-4
- DESC: enhance container behavior
        1.stop docker.socket before uninstall docker.
        2.container keep running when restart docker service.
        3.when containerd exits abnormally, it can be automatically pulled up.
        4.add some dockerd options.
        5.change to BuildRequires golang-1.18.0

* Wed Dec 28 2022 xulei<xulei@xfusion.com> - 20.10.21-3
- DESC: change to BuildRequires golang-1.17.3

* Wed Dec 21 2022 wanglimin<wanglimin@xfusion.com> - 20.10.21-2
- DESC: revert any to interface{} temporarily to allow builtable with golang-1.17.x
-       it will be withdrawed if golang upgrade to 1.18.x in the branch

* Thu Dec 14 2022 wanglimin<wanglimin@xfusion.com> - 20.10.21-1
- DESC: initial docker-20.10.21-1
