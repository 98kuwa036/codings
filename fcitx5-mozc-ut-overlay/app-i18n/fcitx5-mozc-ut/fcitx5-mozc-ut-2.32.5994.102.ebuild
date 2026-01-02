# Copyright 2024-2025 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

PYTHON_COMPAT=( python3_{11..13} )

inherit check-reqs cmake desktop python-any-r1 xdg

MOZC_VER="${PV}"
MOZC_COMMIT="d9c3f195582de6b0baa07ecb81a04e8902acf9af"
FCITX5_MOZC_COMMIT="f9feca5e986ed1a874e6f86122ecc48808a57b1a"

# UT Dictionary commits (latest as of 2025-01)
UT_ALT_CANNADIC_COMMIT="69d40eed4e9cf016384d9629920fefa199116ea2"
UT_EDICT2_COMMIT="aa2decff870dd341ac2ddc20b453f27fc2df3721"
UT_JAWIKI_COMMIT="4590e06f23071be2850b7d53a7fe73728a2572ad"
UT_NEOLOGD_COMMIT="e33ac4ce808fa4253c6c97bf5178e229a4bfb50f"
UT_PERSONAL_NAMES_COMMIT="a64659ba0c8ee34170f09d7fa21dfd5cb5005296"
UT_PLACE_NAMES_COMMIT="2748c881573e4e33e2c20e3ec61dba7e59e8bf9d"
UT_SKK_JISYO_COMMIT="384ad926e306d5308839c6dedb63696f11703968"
UT_SUDACHIDICT_COMMIT="33f9835cfafc85d6761037342debec0e7ae8aa17"

DESCRIPTION="Mozc with Fcitx5 support and all UT dictionaries"
HOMEPAGE="
	https://github.com/google/mozc
	https://github.com/fcitx/mozc
	https://github.com/utuhiro78/merge-ut-dictionaries
"

SRC_URI="
	https://github.com/google/mozc/archive/${MOZC_COMMIT}.tar.gz -> mozc-${MOZC_VER}.tar.gz
	https://github.com/fcitx/mozc/archive/${FCITX5_MOZC_COMMIT}.tar.gz -> fcitx5-mozc-${FCITX5_MOZC_COMMIT}.tar.gz
	https://github.com/utuhiro78/mozcdic-ut-alt-cannadic/archive/${UT_ALT_CANNADIC_COMMIT}.tar.gz -> mozcdic-ut-alt-cannadic-${UT_ALT_CANNADIC_COMMIT}.tar.gz
	https://github.com/utuhiro78/mozcdic-ut-edict2/archive/${UT_EDICT2_COMMIT}.tar.gz -> mozcdic-ut-edict2-${UT_EDICT2_COMMIT}.tar.gz
	https://github.com/utuhiro78/mozcdic-ut-jawiki/archive/${UT_JAWIKI_COMMIT}.tar.gz -> mozcdic-ut-jawiki-${UT_JAWIKI_COMMIT}.tar.gz
	https://github.com/utuhiro78/mozcdic-ut-neologd/archive/${UT_NEOLOGD_COMMIT}.tar.gz -> mozcdic-ut-neologd-${UT_NEOLOGD_COMMIT}.tar.gz
	https://github.com/utuhiro78/mozcdic-ut-personal-names/archive/${UT_PERSONAL_NAMES_COMMIT}.tar.gz -> mozcdic-ut-personal-names-${UT_PERSONAL_NAMES_COMMIT}.tar.gz
	https://github.com/utuhiro78/mozcdic-ut-place-names/archive/${UT_PLACE_NAMES_COMMIT}.tar.gz -> mozcdic-ut-place-names-${UT_PLACE_NAMES_COMMIT}.tar.gz
	https://github.com/utuhiro78/mozcdic-ut-skk-jisyo/archive/${UT_SKK_JISYO_COMMIT}.tar.gz -> mozcdic-ut-skk-jisyo-${UT_SKK_JISYO_COMMIT}.tar.gz
	https://github.com/utuhiro78/mozcdic-ut-sudachidict/archive/${UT_SUDACHIDICT_COMMIT}.tar.gz -> mozcdic-ut-sudachidict-${UT_SUDACHIDICT_COMMIT}.tar.gz
"

S="${WORKDIR}/mozc-${MOZC_COMMIT}"

LICENSE="BSD-3 Apache-2.0 CC-BY-SA-4.0 GPL-2+ LGPL-2.1+ MIT"
SLOT="0"
KEYWORDS="~amd64"
IUSE="emacs gui renderer test"
RESTRICT="!test? ( test )"

BDEPEND="
	${PYTHON_DEPS}
	>=dev-build/bazel-6.4.0
	dev-build/ninja
	virtual/pkgconfig
"

RDEPEND="
	>=app-i18n/fcitx-5.0.0:5
	dev-libs/abseil-cpp:=
	dev-libs/protobuf:=
	emacs? ( app-editors/emacs:* )
	gui? (
		dev-qt/qtbase:6[gui,widgets]
	)
	renderer? (
		dev-qt/qtbase:6[gui,widgets]
		x11-libs/gtk+:3
	)
"

DEPEND="${RDEPEND}"

PATCHES=(
)

pkg_pretend() {
	# Bazel requires significant memory
	if [[ ${MERGE_TYPE} != binary ]]; then
		CHECKREQS_MEMORY="4G"
		check-reqs_pkg_pretend
	fi
}

src_unpack() {
	default

	# Move fcitx5 patch files
	mv "${WORKDIR}/mozc-${FCITX5_MOZC_COMMIT}" "${WORKDIR}/fcitx5-mozc" || die
}

src_prepare() {
	default

	# Apply fcitx5 patches from fcitx/mozc repository
	if [[ -d "${WORKDIR}/fcitx5-mozc/scripts/patches" ]]; then
		eapply "${WORKDIR}/fcitx5-mozc/scripts/patches"/*.patch
	fi

	# Copy fcitx5 module source
	if [[ -d "${WORKDIR}/fcitx5-mozc/src/unix/fcitx5" ]]; then
		cp -r "${WORKDIR}/fcitx5-mozc/src/unix/fcitx5" "${S}/src/unix/" || die
	fi

	# Merge UT dictionaries
	einfo "Merging UT dictionaries..."

	local dict_file="${S}/src/data/dictionary_oss/dictionary00.txt"

	# alt-cannadic
	if [[ -f "${WORKDIR}/mozcdic-ut-alt-cannadic-${UT_ALT_CANNADIC_COMMIT}/mozcdic-ut-alt-cannadic.txt" ]]; then
		cat "${WORKDIR}/mozcdic-ut-alt-cannadic-${UT_ALT_CANNADIC_COMMIT}/mozcdic-ut-alt-cannadic.txt" >> "${dict_file}" || die
		einfo "  Added: alt-cannadic"
	fi

	# edict2
	if [[ -f "${WORKDIR}/mozcdic-ut-edict2-${UT_EDICT2_COMMIT}/mozcdic-ut-edict2.txt" ]]; then
		cat "${WORKDIR}/mozcdic-ut-edict2-${UT_EDICT2_COMMIT}/mozcdic-ut-edict2.txt" >> "${dict_file}" || die
		einfo "  Added: edict2"
	fi

	# jawiki
	if [[ -f "${WORKDIR}/mozcdic-ut-jawiki-${UT_JAWIKI_COMMIT}/mozcdic-ut-jawiki.txt" ]]; then
		cat "${WORKDIR}/mozcdic-ut-jawiki-${UT_JAWIKI_COMMIT}/mozcdic-ut-jawiki.txt" >> "${dict_file}" || die
		einfo "  Added: jawiki"
	fi

	# neologd
	if [[ -f "${WORKDIR}/mozcdic-ut-neologd-${UT_NEOLOGD_COMMIT}/mozcdic-ut-neologd.txt" ]]; then
		cat "${WORKDIR}/mozcdic-ut-neologd-${UT_NEOLOGD_COMMIT}/mozcdic-ut-neologd.txt" >> "${dict_file}" || die
		einfo "  Added: neologd"
	fi

	# personal-names
	if [[ -f "${WORKDIR}/mozcdic-ut-personal-names-${UT_PERSONAL_NAMES_COMMIT}/mozcdic-ut-personal-names.txt" ]]; then
		cat "${WORKDIR}/mozcdic-ut-personal-names-${UT_PERSONAL_NAMES_COMMIT}/mozcdic-ut-personal-names.txt" >> "${dict_file}" || die
		einfo "  Added: personal-names"
	fi

	# place-names
	if [[ -f "${WORKDIR}/mozcdic-ut-place-names-${UT_PLACE_NAMES_COMMIT}/mozcdic-ut-place-names.txt" ]]; then
		cat "${WORKDIR}/mozcdic-ut-place-names-${UT_PLACE_NAMES_COMMIT}/mozcdic-ut-place-names.txt" >> "${dict_file}" || die
		einfo "  Added: place-names"
	fi

	# skk-jisyo
	if [[ -f "${WORKDIR}/mozcdic-ut-skk-jisyo-${UT_SKK_JISYO_COMMIT}/mozcdic-ut-skk-jisyo.txt" ]]; then
		cat "${WORKDIR}/mozcdic-ut-skk-jisyo-${UT_SKK_JISYO_COMMIT}/mozcdic-ut-skk-jisyo.txt" >> "${dict_file}" || die
		einfo "  Added: skk-jisyo"
	fi

	# sudachidict
	if [[ -f "${WORKDIR}/mozcdic-ut-sudachidict-${UT_SUDACHIDICT_COMMIT}/mozcdic-ut-sudachidict.txt" ]]; then
		cat "${WORKDIR}/mozcdic-ut-sudachidict-${UT_SUDACHIDICT_COMMIT}/mozcdic-ut-sudachidict.txt" >> "${dict_file}" || die
		einfo "  Added: sudachidict"
	fi

	einfo "UT dictionary merge complete."
}

src_configure() {
	:
}

src_compile() {
	cd "${S}/src" || die

	local bazel_args=(
		"--config=linux"
		"--compilation_mode=opt"
		"--copt=-Wno-error"
		"--host_copt=-Wno-error"
	)

	# Build mozc_server
	einfo "Building mozc_server..."
	bazel build "${bazel_args[@]}" \
		server:mozc_server || die "mozc_server build failed"

	# Build fcitx5 module
	einfo "Building fcitx5 module..."
	bazel build "${bazel_args[@]}" \
		unix/fcitx5:fcitx5-mozc || die "fcitx5-mozc build failed"

	# Build optional components
	if use emacs; then
		einfo "Building emacs helper..."
		bazel build "${bazel_args[@]}" \
			unix/emacs:mozc_emacs_helper || die
	fi

	if use gui; then
		einfo "Building mozc_tool..."
		bazel build "${bazel_args[@]}" \
			gui/tool:mozc_tool || die
	fi

	if use renderer; then
		einfo "Building mozc_renderer..."
		bazel build "${bazel_args[@]}" \
			renderer:mozc_renderer || die
	fi
}

src_install() {
	cd "${S}/src" || die

	local bazel_out="${S}/src/bazel-out/k8-opt/bin"

	# Install mozc_server
	exeinto /usr/libexec/mozc
	doexe "${bazel_out}/server/mozc_server"

	# Install fcitx5 module
	insinto /usr/$(get_libdir)/fcitx5
	doins "${bazel_out}/unix/fcitx5/fcitx5-mozc.so"

	# Install fcitx5 addon config
	insinto /usr/share/fcitx5/addon
	doins "${WORKDIR}/fcitx5-mozc/src/unix/fcitx5/mozc-addon.conf"

	insinto /usr/share/fcitx5/inputmethod
	doins "${WORKDIR}/fcitx5-mozc/src/unix/fcitx5/mozc.conf"

	# Install icons
	local icon_sizes="16 22 24 32 48 64 128 256"
	for size in ${icon_sizes}; do
		if [[ -f "${S}/data/images/product_icon_${size}.png" ]]; then
			newicon -s ${size} \
				"${S}/data/images/product_icon_${size}.png" \
				fcitx5-mozc.png
		fi
	done

	# Install emacs support
	if use emacs; then
		exeinto /usr/libexec/mozc
		doexe "${bazel_out}/unix/emacs/mozc_emacs_helper"

		insinto /usr/share/emacs/site-lisp/mozc
		doins "${S}/src/unix/emacs/mozc.el"
	fi

	# Install GUI tool
	if use gui; then
		exeinto /usr/libexec/mozc
		doexe "${bazel_out}/gui/tool/mozc_tool"

		make_desktop_entry \
			"/usr/libexec/mozc/mozc_tool --mode=config_dialog" \
			"Mozc Setup" \
			fcitx5-mozc \
			"Settings;IBus;Qt"

		make_desktop_entry \
			"/usr/libexec/mozc/mozc_tool --mode=dictionary_tool" \
			"Mozc Dictionary Tool" \
			fcitx5-mozc \
			"Office;Dictionary;Qt"
	fi

	# Install renderer
	if use renderer; then
		exeinto /usr/libexec/mozc
		doexe "${bazel_out}/renderer/mozc_renderer"
	fi
}

pkg_postinst() {
	xdg_pkg_postinst

	elog "Mozc with fcitx5 support and UT dictionaries has been installed."
	elog ""
	elog "Included UT dictionaries (all selected):"
	elog "  - alt-cannadic: Alternative Cannadic dictionary"
	elog "  - edict2: Japanese-English dictionary"
	elog "  - jawiki: Japanese Wikipedia dictionary"
	elog "  - neologd: Neologism dictionary"
	elog "  - personal-names: Personal name dictionary"
	elog "  - place-names: Place name dictionary"
	elog "  - skk-jisyo: SKK Japanese dictionary"
	elog "  - sudachidict: Sudachi morphological dictionary"
	elog ""
	elog "To use fcitx5-mozc, add 'mozc' to your fcitx5 input methods."
	elog ""
	if use gui; then
		elog "Run 'mozc_tool --mode=config_dialog' to configure Mozc."
	fi
}
