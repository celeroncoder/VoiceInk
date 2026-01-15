desktop_file = i18n.merge_file(
  input: 'org.voiceink.VoiceInk.desktop.in',
  output: 'org.voiceink.VoiceInk.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

install_data('org.voiceink.VoiceInk.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file',
    compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

gnome.compile_resources('voiceink',
  'voiceink.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)
