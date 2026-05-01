"""
Unified LLM Provider for multi-model testing
Supports: OpenAI, Google Gemini, Anthropic Claude, HuggingFace
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    provider: str  # "openai", "gemini", "anthropic", "huggingface"
    model_id: str
    name: str = ""
    temperature: float = 0.1
    max_tokens: int = 1000
    top_p: float = 1.0
    api_key: Optional[str] = None


class UnifiedLLMProvider:
    """
    Unified interface for multiple LLM providers.
    Handles generation, error handling, and logging.
    """
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.provider_name = config.provider
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate client based on provider"""
        try:
            if self.config.provider == "openai":
                from openai import OpenAI
                api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
                self.client = OpenAI(api_key=api_key)
                logger.info(f"✓ Initialized OpenAI client for {self.config.model_id}")
            
            elif self.config.provider == "gemini":
                from google import genai
                from google.genai import types
                api_key = self.config.api_key or os.getenv("GEMINI_API_KEY")
                self.client = genai.Client(api_key=api_key)
                self._gemini_types = types
                logger.info(f"✓ Initialized Gemini client for {self.config.model_id}")
            
            elif self.config.provider == "anthropic":
                from anthropic import Anthropic
                api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
                self.client = Anthropic(api_key=api_key)
                logger.info(f"✓ Initialized Anthropic client for {self.config.model_id}")
            
            elif self.config.provider == "huggingface":
                from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
                import torch

                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.config.model_id,
                    trust_remote_code=True,
                )
                model = AutoModelForCausalLM.from_pretrained(
                    self.config.model_id,
                    torch_dtype=torch.float32,
                    trust_remote_code=True,
                )
                self.client = pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=self.tokenizer,
                    device=-1,
                )
                logger.info(f"✓ Initialized HuggingFace client for {self.config.model_id}")
            
            else:
                raise ValueError(f"Unsupported provider: {self.config.provider}")
        
        except Exception as e:
            logger.error(f"Failed to initialize {self.config.provider} client: {e}")
            raise
    
    def generate(self, prompt: str, system_message: Optional[str] = None) -> str:
        """
        Generate response from the LLM.
        
        Args:
            prompt: The user prompt/question
            system_message: Optional system context/instructions
        
        Returns:
            Generated response text
        """
        try:
            if self.config.provider == "openai":
                return self._generate_openai(prompt, system_message)
            elif self.config.provider == "gemini":
                return self._generate_gemini(prompt, system_message)
            elif self.config.provider == "anthropic":
                return self._generate_anthropic(prompt, system_message)
            elif self.config.provider == "huggingface":
                return self._generate_huggingface(prompt, system_message)
        except Exception as e:
            logger.error(f"Generation failed for {self.config.model_id}: {e}")
            return ""
    
    def _generate_openai(self, prompt: str, system_message: Optional[str]) -> str:
        """OpenAI API call"""
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.config.model_id,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p
        )
        return response.choices[0].message.content
    
    def _generate_gemini(self, prompt: str, system_message: Optional[str]) -> str:
        """Google Gemini API call"""
        full_prompt = prompt
        if system_message:
            full_prompt = f"{system_message}\n\n{prompt}"
        
        response = self.client.models.generate_content(
            model=self.config.model_id,
            contents=full_prompt,
            config=self._gemini_types.GenerateContentConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            ),
        )
        return response.text if getattr(response, "text", None) else ""
    
    def _generate_anthropic(self, prompt: str, system_message: Optional[str]) -> str:
        """Anthropic Claude API call"""
        messages = [{"role": "user", "content": prompt}]
        
        response = self.client.messages.create(
            model=self.config.model_id,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            system=system_message,
            messages=messages
        )
        return response.content[0].text
    
    def _generate_huggingface(self, prompt: str, system_message: Optional[str]) -> str:
        """HuggingFace Inference API call"""
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        if getattr(self.tokenizer, "chat_template", None):
            full_prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt

        generation_kwargs = {
            "max_new_tokens": self.config.max_tokens,
            "return_full_text": False,
            "do_sample": self.config.temperature > 0,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
        }
        response = self.client(full_prompt, **generation_kwargs)
        if isinstance(response, list) and response:
            return response[0].get("generated_text", "")
        if isinstance(response, dict):
            return response.get("generated_text", "")
        return str(response)
    
    def batch_generate(self, prompts: List[str], system_message: Optional[str] = None) -> List[str]:
        """
        Generate responses for multiple prompts.
        
        Args:
            prompts: List of prompts
            system_message: Optional system context
        
        Returns:
            List of generated responses
        """
        results = []
        for i, prompt in enumerate(prompts):
            logger.info(f"Processing prompt {i+1}/{len(prompts)} for {self.config.model_id}")
            response = self.generate(prompt, system_message)
            results.append(response)
        return results
    
    def __repr__(self) -> str:
        return f"UnifiedLLMProvider({self.config.provider}/{self.config.model_id})"
