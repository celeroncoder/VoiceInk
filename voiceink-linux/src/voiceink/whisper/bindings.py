"""ctypes bindings for whisper.cpp (libwhisper.so)"""

import ctypes
import os
import numpy as np
from ctypes import (
    c_int, c_int32, c_float, c_char_p, c_void_p, c_bool,
    POINTER, Structure, byref
)
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class WhisperError(Exception):
    """Whisper library error"""
    pass


# Whisper sampling strategy enum
WHISPER_SAMPLING_GREEDY = 0
WHISPER_SAMPLING_BEAM_SEARCH = 1


class WhisperContextParams(Structure):
    """whisper_context_params structure"""
    _fields_ = [
        ("use_gpu", c_bool),
        ("flash_attn", c_bool),
        ("gpu_device", c_int),
        ("dtw_token_timestamps", c_bool),
        ("dtw_aheads_preset", c_int),
        ("dtw_n_top", c_int),
        ("dtw_aheads", c_void_p),
        ("dtw_mem_size", ctypes.c_size_t),
    ]


class WhisperFullParams(Structure):
    """whisper_full_params structure - simplified version with key fields"""
    _fields_ = [
        ("strategy", c_int),
        ("n_threads", c_int),
        ("n_max_text_ctx", c_int),
        ("offset_ms", c_int),
        ("duration_ms", c_int),
        ("translate", c_bool),
        ("no_context", c_bool),
        ("no_timestamps", c_bool),
        ("single_segment", c_bool),
        ("print_special", c_bool),
        ("print_progress", c_bool),
        ("print_realtime", c_bool),
        ("print_timestamps", c_bool),
        ("token_timestamps", c_bool),
        ("thold_pt", c_float),
        ("thold_ptsum", c_float),
        ("max_len", c_int),
        ("split_on_word", c_bool),
        ("max_tokens", c_int),
        ("debug_mode", c_bool),
        ("audio_ctx", c_int),
        ("tdrz_enable", c_bool),
        ("suppress_regex", c_char_p),
        ("initial_prompt", c_char_p),
        ("prompt_tokens", c_void_p),
        ("prompt_n_tokens", c_int),
        ("language", c_char_p),
        ("detect_language", c_bool),
        ("suppress_blank", c_bool),
        ("suppress_nst", c_bool),
        ("temperature", c_float),
        ("max_initial_ts", c_float),
        ("length_penalty", c_float),
        ("temperature_inc", c_float),
        ("entropy_thold", c_float),
        ("logprob_thold", c_float),
        ("no_speech_thold", c_float),
        ("greedy", c_int * 1),
        ("beam_search", c_int * 3),
        # Callbacks - set to NULL for now
        ("new_segment_callback", c_void_p),
        ("new_segment_callback_user_data", c_void_p),
        ("progress_callback", c_void_p),
        ("progress_callback_user_data", c_void_p),
        ("encoder_begin_callback", c_void_p),
        ("encoder_begin_callback_user_data", c_void_p),
        ("abort_callback", c_void_p),
        ("abort_callback_user_data", c_void_p),
        ("logits_filter_callback", c_void_p),
        ("logits_filter_callback_user_data", c_void_p),
        ("grammar_rules", c_void_p),
        ("n_grammar_rules", ctypes.c_size_t),
        ("i_start_rule", ctypes.c_size_t),
        ("grammar_penalty", c_float),
    ]


def _find_library() -> Optional[Path]:
    """Find libwhisper.so in common locations"""
    search_paths = [
        Path.home() / ".local" / "lib" / "libwhisper.so",
        Path("/usr/local/lib/libwhisper.so"),
        Path("/usr/lib/libwhisper.so"),
        Path("/usr/lib/x86_64-linux-gnu/libwhisper.so"),
        Path.cwd() / "libwhisper.so",
        Path(__file__).parent.parent.parent.parent / "lib" / "libwhisper.so",
    ]

    # Check LD_LIBRARY_PATH
    ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    for path in ld_path.split(":"):
        if path:
            search_paths.append(Path(path) / "libwhisper.so")

    for path in search_paths:
        if path.exists():
            return path

    return None


class WhisperContext:
    """Wrapper for whisper context with transcription capabilities"""

    _lib: Optional[ctypes.CDLL] = None
    _lib_path: Optional[Path] = None

    @classmethod
    def _load_library(cls) -> ctypes.CDLL:
        """Load the whisper shared library"""
        if cls._lib is not None:
            return cls._lib

        lib_path = _find_library()
        if lib_path is None:
            raise WhisperError(
                "libwhisper.so not found. Please compile whisper.cpp and install:\n"
                "  git clone https://github.com/ggerganov/whisper.cpp\n"
                "  cd whisper.cpp\n"
                "  cmake -B build -DBUILD_SHARED_LIBS=ON\n"
                "  cmake --build build --config Release\n"
                "  cp build/libwhisper.so ~/.local/lib/"
            )

        try:
            lib = ctypes.CDLL(str(lib_path))
            cls._lib_path = lib_path
        except OSError as e:
            raise WhisperError(f"Failed to load {lib_path}: {e}")

        # Define function signatures
        # whisper_init_from_file_with_params
        lib.whisper_init_from_file_with_params.argtypes = [c_char_p, WhisperContextParams]
        lib.whisper_init_from_file_with_params.restype = c_void_p

        # whisper_context_default_params
        lib.whisper_context_default_params.argtypes = []
        lib.whisper_context_default_params.restype = WhisperContextParams

        # whisper_full_default_params
        lib.whisper_full_default_params.argtypes = [c_int]
        lib.whisper_full_default_params.restype = WhisperFullParams

        # whisper_full
        lib.whisper_full.argtypes = [c_void_p, WhisperFullParams, POINTER(c_float), c_int]
        lib.whisper_full.restype = c_int

        # whisper_full_n_segments
        lib.whisper_full_n_segments.argtypes = [c_void_p]
        lib.whisper_full_n_segments.restype = c_int

        # whisper_full_get_segment_text
        lib.whisper_full_get_segment_text.argtypes = [c_void_p, c_int]
        lib.whisper_full_get_segment_text.restype = c_char_p

        # whisper_free
        lib.whisper_free.argtypes = [c_void_p]
        lib.whisper_free.restype = None

        # whisper_reset_timings
        lib.whisper_reset_timings.argtypes = [c_void_p]
        lib.whisper_reset_timings.restype = None

        cls._lib = lib
        logger.info(f"Loaded whisper library from {lib_path}")
        return lib

    def __init__(self, model_path: str, use_gpu: bool = True):
        """Initialize whisper context with a model file

        Args:
            model_path: Path to the .bin model file
            use_gpu: Whether to use GPU acceleration (CUDA)
        """
        self._lib = self._load_library()
        self._ctx: Optional[c_void_p] = None
        self._language: Optional[str] = None
        self._initial_prompt: Optional[str] = None

        if not Path(model_path).exists():
            raise WhisperError(f"Model file not found: {model_path}")

        # Get default context params and configure
        params = self._lib.whisper_context_default_params()
        params.use_gpu = use_gpu
        params.flash_attn = use_gpu  # Enable flash attention when using GPU

        # Initialize the context
        ctx = self._lib.whisper_init_from_file_with_params(
            model_path.encode('utf-8'),
            params
        )

        if not ctx:
            raise WhisperError(f"Failed to load model: {model_path}")

        self._ctx = ctx
        self._model_path = model_path
        logger.info(f"Loaded whisper model: {model_path}")

    def __del__(self):
        self.free()

    def free(self):
        """Free the whisper context"""
        if self._ctx is not None and self._lib is not None:
            self._lib.whisper_free(self._ctx)
            self._ctx = None
            logger.debug("Freed whisper context")

    def set_language(self, language: Optional[str]):
        """Set the language for transcription (None for auto-detect)"""
        self._language = language

    def set_initial_prompt(self, prompt: Optional[str]):
        """Set the initial prompt for transcription context"""
        self._initial_prompt = prompt

    def transcribe(
        self,
        samples: np.ndarray,
        n_threads: Optional[int] = None,
        translate: bool = False,
        temperature: float = 0.0,
    ) -> str:
        """Transcribe audio samples

        Args:
            samples: Audio samples as float32 numpy array, mono, 16kHz
            n_threads: Number of threads to use (default: auto)
            translate: Whether to translate to English
            temperature: Sampling temperature

        Returns:
            Transcribed text
        """
        if self._ctx is None:
            raise WhisperError("Context not initialized")

        # Ensure samples are float32 and contiguous
        if samples.dtype != np.float32:
            samples = samples.astype(np.float32)
        samples = np.ascontiguousarray(samples)

        # Get default params
        params = self._lib.whisper_full_default_params(WHISPER_SAMPLING_GREEDY)

        # Configure params
        if n_threads is None:
            n_threads = max(1, min(8, os.cpu_count() - 2))
        params.n_threads = n_threads

        params.translate = translate
        params.temperature = temperature
        params.no_context = True
        params.single_segment = False
        params.print_realtime = False
        params.print_progress = False
        params.print_timestamps = False
        params.print_special = False

        # Set language
        if self._language and self._language != "auto":
            params.language = self._language.encode('utf-8')
        else:
            params.language = None
            params.detect_language = True

        # Set initial prompt
        if self._initial_prompt:
            params.initial_prompt = self._initial_prompt.encode('utf-8')

        # Reset timings
        self._lib.whisper_reset_timings(self._ctx)

        # Run transcription
        samples_ptr = samples.ctypes.data_as(POINTER(c_float))
        result = self._lib.whisper_full(
            self._ctx,
            params,
            samples_ptr,
            len(samples)
        )

        if result != 0:
            raise WhisperError(f"Transcription failed with code {result}")

        # Get transcription text
        n_segments = self._lib.whisper_full_n_segments(self._ctx)
        text_parts = []

        for i in range(n_segments):
            segment_text = self._lib.whisper_full_get_segment_text(self._ctx, i)
            if segment_text:
                text_parts.append(segment_text.decode('utf-8'))

        return "".join(text_parts)

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._ctx is not None
