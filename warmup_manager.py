"""
Intelligent warming system for Node.js/Claude CLI to eliminate cold starts.
"""

import asyncio
import logging
import time
import os
from typing import Optional, Literal
from enum import Enum

logger = logging.getLogger(__name__)

class WarmupStrategy(str, Enum):
    NONE = "none"
    PERIODIC = "periodic"
    PERSISTENT = "persistent"
    ADAPTIVE = "adaptive"

class WarmupManager:
    """
    Manages Node.js/Claude CLI warming to eliminate cold start latency.
    
    Strategies:
    - none: No warming (default behavior)
    - periodic: Refresh cache at intervals
    - persistent: Keep Node.js process always running
    - adaptive: Switch between periodic/persistent based on load
    """
    
    def __init__(
        self,
        strategy: WarmupStrategy = WarmupStrategy.NONE,
        refresh_seconds: int = 30,
        persistent_threshold: int = 10,
        idle_timeout: int = 300,
        skip_verification: bool = True
    ):
        """
        Initialize warmup manager.
        
        Args:
            strategy: Warming strategy to use
            refresh_seconds: Interval for periodic refresh
            persistent_threshold: Requests/min to trigger persistent mode
            idle_timeout: Seconds of inactivity before stopping warmup
            skip_verification: Skip CLI verification on startup
        """
        self.strategy = strategy
        self.refresh_seconds = refresh_seconds
        self.persistent_threshold = persistent_threshold
        self.idle_timeout = idle_timeout
        self.skip_verification = skip_verification
        
        # State tracking
        self.persistent_process: Optional[asyncio.subprocess.Process] = None
        self.refresh_task: Optional[asyncio.Task] = None
        self.last_request_time: float = 0
        self.request_count: int = 0
        self.request_window_start: float = time.time()
        self.is_persistent_mode: bool = False
        
        # Statistics
        self.warmup_count: int = 0
        self.warmup_failures: int = 0
        self.total_warmup_time: float = 0
        
    async def start(self):
        """Start the warmup manager based on configured strategy."""
        if self.strategy == WarmupStrategy.NONE:
            logger.info("Warmup disabled (strategy=none)")
            return
            
        logger.info(f"Starting warmup manager with strategy: {self.strategy}")
        
        # Perform initial warmup on startup for all strategies except none
        logger.info("🚀 Performing initial warmup on startup...")
        await self._warm_nodejs()
        
        if self.strategy == WarmupStrategy.PERSISTENT:
            await self._start_persistent()
        elif self.strategy in (WarmupStrategy.PERIODIC, WarmupStrategy.ADAPTIVE):
            self.refresh_task = asyncio.create_task(self._periodic_refresh_loop())
            
    async def stop(self):
        """Stop all warmup activities and cleanup."""
        logger.info("Stopping warmup manager")
        
        # Cancel refresh task
        if self.refresh_task:
            self.refresh_task.cancel()
            try:
                await self.refresh_task
            except asyncio.CancelledError:
                pass
                
        # Terminate persistent process
        if self.persistent_process:
            await self._stop_persistent()
            
    async def on_request(self):
        """
        Called when an API request is received.
        Updates statistics and triggers adaptive behavior.
        """
        self.last_request_time = time.time()
        self.request_count += 1
        
        # Reset request window every minute
        if time.time() - self.request_window_start > 60:
            rpm = self.request_count  # Requests per minute
            
            if self.strategy == WarmupStrategy.ADAPTIVE:
                await self._adapt_strategy(rpm)
                
            self.request_count = 0
            self.request_window_start = time.time()
            
    async def _adapt_strategy(self, rpm: int):
        """
        Adapt warming strategy based on request rate.
        
        Args:
            rpm: Requests per minute
        """
        if rpm >= self.persistent_threshold and not self.is_persistent_mode:
            logger.info(f"High activity detected ({rpm} rpm) - switching to persistent mode")
            await self._start_persistent()
            self.is_persistent_mode = True
            
        elif rpm < self.persistent_threshold / 2 and self.is_persistent_mode:
            logger.info(f"Low activity detected ({rpm} rpm) - switching to periodic mode")
            await self._stop_persistent()
            self.is_persistent_mode = False
            
    async def _periodic_refresh_loop(self):
        """Main loop for periodic refresh strategy."""
        while True:
            try:
                await asyncio.sleep(self.refresh_seconds)
                
                # Check if we should warm based on recent activity
                if self._should_warm():
                    logger.info(f"🔄 Starting warmup cycle (strategy: {self.strategy.value})")
                    await self._warm_nodejs()
                else:
                    logger.debug(f"Skipping warmup - idle for {time.time() - self.last_request_time:.1f}s")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in refresh loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
                
    def _should_warm(self) -> bool:
        """Determine if warming should occur based on activity."""
        if self.strategy == WarmupStrategy.PERIODIC:
            return True  # Always warm in periodic mode
            
        # For adaptive mode, only warm if recent activity
        time_since_last = time.time() - self.last_request_time
        return time_since_last < self.idle_timeout
        
    async def _warm_nodejs(self):
        """
        Warm Node.js/Claude CLI without making API calls.
        Uses multiple methods with fallbacks.
        """
        start_time = time.time()
        
        try:
            # Method 1: Direct module loading (fastest, most reliable)
            success = await self._warm_via_node_require()
            
            if not success:
                # Method 2: CLI help command
                success = await self._warm_via_cli_help()
                
            if success:
                self.warmup_count += 1
                elapsed = time.time() - start_time
                self.total_warmup_time += elapsed
                logger.info(f"🔥 Warmup #{self.warmup_count} completed in {elapsed:.2f}s")
            else:
                self.warmup_failures += 1
                logger.warning(f"Warmup failed (total failures: {self.warmup_failures})")
                
        except Exception as e:
            self.warmup_failures += 1
            logger.error(f"Warmup error: {e}")
            
    async def _warm_via_node_require(self) -> bool:
        """
        Warm by directly loading Node.js modules.
        Returns True if successful.
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "node",
                "-e",
                "try { require('@anthropic-ai/claude-code'); console.log('ok'); } catch(e) { process.exit(1); }",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=5.0
            )
            
            return process.returncode == 0 and b"ok" in stdout
            
        except (asyncio.TimeoutError, FileNotFoundError):
            return False
            
    async def _warm_via_cli_help(self) -> bool:
        """
        Warm by running claude --help command.
        Returns True if successful.
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "claude",
                "--help",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            await asyncio.wait_for(
                process.wait(),
                timeout=5.0
            )
            
            return process.returncode == 0
            
        except (asyncio.TimeoutError, FileNotFoundError):
            return False
            
    async def _start_persistent(self):
        """Start a persistent Node.js process to keep modules loaded."""
        if self.persistent_process:
            return  # Already running
            
        try:
            logger.info("Starting persistent Node.js warmup process")
            
            self.persistent_process = await asyncio.create_subprocess_exec(
                "node",
                "-e",
                """
                const claude = require('@anthropic-ai/claude-code');
                console.log('Persistent warmup process started');
                
                // Keep process alive and modules in memory
                setInterval(() => {
                    // Touch modules periodically to prevent GC
                    if (claude && typeof claude === 'object') {
                        Object.keys(claude).length;  // Keep reference active
                    }
                }, 60000);  // Every minute
                
                // Handle termination gracefully
                process.on('SIGTERM', () => {
                    console.log('Warmup process terminating');
                    process.exit(0);
                });
                """,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Verify it started successfully
            await asyncio.sleep(0.5)
            if self.persistent_process.returncode is None:
                logger.info("Persistent warmup process running")
            else:
                logger.error("Persistent warmup process failed to start")
                self.persistent_process = None
                
        except Exception as e:
            logger.error(f"Failed to start persistent process: {e}")
            self.persistent_process = None
            
    async def _stop_persistent(self):
        """Stop the persistent Node.js process."""
        if not self.persistent_process:
            return
            
        try:
            logger.info("Stopping persistent warmup process")
            self.persistent_process.terminate()
            await asyncio.wait_for(
                self.persistent_process.wait(),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning("Persistent process didn't terminate, killing")
            self.persistent_process.kill()
            await self.persistent_process.wait()
        finally:
            self.persistent_process = None
            
    def get_stats(self) -> dict:
        """Get warmup statistics."""
        avg_time = (
            self.total_warmup_time / self.warmup_count 
            if self.warmup_count > 0 else 0
        )
        
        return {
            "strategy": self.strategy.value,
            "is_persistent_mode": self.is_persistent_mode,
            "warmup_count": self.warmup_count,
            "warmup_failures": self.warmup_failures,
            "average_warmup_time": round(avg_time, 3),
            "last_request_ago": round(time.time() - self.last_request_time, 1),
            "current_rpm": self.request_count,  # Within current minute
        }