"""
Configuration manager for persistent Janus Diff settings.

Manages ~/.janus/config.json for LLM and other settings.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any


class ConfigManager:
    """Manage Janus Diff configuration."""
    
    CONFIG_DIR = Path.home() / ".janus"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    
    def __init__(self):
        """Initialize config manager."""
        self.config_path = self.CONFIG_FILE
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure config directory exists."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dict or None if file doesn't exist
        """
        if not self.CONFIG_FILE.exists():
            return None
        
        try:
            with open(self.CONFIG_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠ Warning: Could not parse {self.CONFIG_FILE}")
            return None
    
    def save(self, config: Dict[str, Any]):
        """
        Save configuration to file.
        
        Args:
            config: Configuration dictionary
        """
        self._ensure_config_dir()
        
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key (supports dot notation: llm.type)
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        config = self.load()
        if not config:
            return default
        
        # Support nested keys with dot notation
        keys = key.split(".")
        value = config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
    
    def set_llm_local(self, url: str, model: Optional[str] = None):
        """
        Configure local LLM (Ollama).
        
        Args:
            url: Ollama endpoint URL
            model: Model name (optional, defaults to mistral)
        """
        config = self.load() or {}
        
        if "llm" not in config:
            config["llm"] = {}
        
        config["llm"]["type"] = "local"
        config["llm"]["url"] = url
        if model:
            config["llm"]["model"] = model
        else:
            config["llm"]["model"] = "mistral"
        
        self.save(config)
    
    def set_llm_online(self, api_key: str, model: Optional[str] = None):
        """
        Configure online LLM (OpenAI).
        
        Args:
            api_key: OpenAI API key
            model: Model name (optional, defaults to gpt-4)
        """
        config = self.load() or {}
        
        if "llm" not in config:
            config["llm"] = {}
        
        config["llm"]["type"] = "online"
        config["llm"]["api_key"] = api_key
        if model:
            config["llm"]["model"] = model
        else:
            config["llm"]["model"] = "gpt-4"
        
        self.save(config)
    
    def get_llm_config(self) -> Optional[Dict[str, str]]:
        """
        Get LLM configuration.
        
        Returns:
            LLM config dict or None if not configured
        """
        config = self.load()
        if config:
            return config.get("llm")
        return None
    
    def get_llm_type(self) -> Optional[str]:
        """
        Get configured LLM type.
        
        Returns:
            "local", "online", or None
        """
        return self.get("llm.type")
    
    def get_llm_url(self) -> Optional[str]:
        """Get Ollama URL."""
        return self.get("llm.url")
    
    def get_llm_api_key(self) -> Optional[str]:
        """Get OpenAI API key."""
        return self.get("llm.api_key")
    
    def get_llm_model(self) -> Optional[str]:
        """Get LLM model name."""
        return self.get("llm.model", "mistral")
    
    def has_llm_config(self) -> bool:
        """Check if LLM is configured."""
        return self.get_llm_type() is not None
    
    def clear(self):
        """Clear all configuration."""
        if self.CONFIG_FILE.exists():
            self.CONFIG_FILE.unlink()
    
    def __repr__(self) -> str:
        """String representation."""
        config = self.load()
        return f"ConfigManager({self.CONFIG_FILE}, {config})"
