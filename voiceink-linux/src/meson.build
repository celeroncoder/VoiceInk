pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'voiceink'

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'voiceink.in',
  output: 'voiceink',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

# Main package files
install_data([
    'voiceink/__init__.py',
    'voiceink/main.py',
    'voiceink/application.py',
    'voiceink/window.py',
  ],
  install_dir: moduledir
)

# Audio module
install_data([
    'voiceink/audio/__init__.py',
    'voiceink/audio/device_manager.py',
    'voiceink/audio/recorder.py',
    'voiceink/audio/utils.py',
  ],
  install_dir: moduledir / 'audio'
)

# Database module
install_data([
    'voiceink/database/__init__.py',
    'voiceink/database/connection.py',
    'voiceink/database/repository.py',
  ],
  install_dir: moduledir / 'database'
)

# Models module
install_data([
    'voiceink/models/__init__.py',
    'voiceink/models/power_mode.py',
    'voiceink/models/transcription.py',
    'voiceink/models/vocabulary.py',
  ],
  install_dir: moduledir / 'models'
)

# Services module
install_data([
    'voiceink/services/__init__.py',
    'voiceink/services/active_window.py',
    'voiceink/services/ai_enhancement.py',
    'voiceink/services/autostart_manager.py',
    'voiceink/services/clipboard_manager.py',
    'voiceink/services/credentials.py',
    'voiceink/services/history_service.py',
    'voiceink/services/hotkey_manager.py',
    'voiceink/services/local_transcription.py',
    'voiceink/services/notification_service.py',
    'voiceink/services/power_mode_manager.py',
    'voiceink/services/service_registry.py',
    'voiceink/services/tray_manager.py',
    'voiceink/services/vocabulary_service.py',
  ],
  install_dir: moduledir / 'services'
)

# Cloud services submodule
install_data([
    'voiceink/services/cloud/__init__.py',
    'voiceink/services/cloud/base.py',
    'voiceink/services/cloud/deepgram_service.py',
    'voiceink/services/cloud/groq_service.py',
    'voiceink/services/cloud/openai_service.py',
  ],
  install_dir: moduledir / 'services' / 'cloud'
)

# Views module
install_data([
    'voiceink/views/__init__.py',
    'voiceink/views/history_view.py',
    'voiceink/views/preferences_window.py',
    'voiceink/views/recording_view.py',
    'voiceink/views/transcription_view.py',
  ],
  install_dir: moduledir / 'views'
)

# Whisper module
install_data([
    'voiceink/whisper/__init__.py',
    'voiceink/whisper/bindings.py',
    'voiceink/whisper/model_manager.py',
    'voiceink/whisper/state.py',
  ],
  install_dir: moduledir / 'whisper'
)
