#!/usr/bin/env python3
"""Deployment script for CPR-NFL system"""
import sys
import os
from pathlib import Path
import asyncio
import logging
import json
import subprocess
from datetime import datetime
import shutil

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentManager:
    """Deployment automation for CPR-NFL system"""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.deployment_log = []
        
    def log_deployment(self, message: str, level: str = "INFO"):
        """Log deployment activity"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message
        }
        self.deployment_log.append(log_entry)
        
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    
    def check_prerequisites(self) -> bool:
        """Check deployment prerequisites"""
        self.log_deployment("🔍 Checking deployment prerequisites...")
        
        prerequisites = {
            "python": False,
            "node": False,
            "firebase": False,
            "docker": False
        }
        
        # Check Python
        try:
            result = subprocess.run(["python3", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                prerequisites["python"] = True
                self.log_deployment(f"✅ Python: {result.stdout.strip()}")
        except Exception as e:
            self.log_deployment("❌ Python not found", "ERROR")
        
        # Check Node.js
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                prerequisites["node"] = True
                self.log_deployment(f"✅ Node.js: {result.stdout.strip()}")
        except Exception as e:
            self.log_deployment("❌ Node.js not found", "ERROR")
        
        # Check Firebase CLI
        try:
            result = subprocess.run(["firebase", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                prerequisites["firebase"] = True
                self.log_deployment(f"✅ Firebase CLI: {result.stdout.strip()}")
        except Exception as e:
            self.log_deployment("❌ Firebase CLI not found", "WARNING")
        
        # Check Docker
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                prerequisites["docker"] = True
                self.log_deployment(f"✅ Docker: {result.stdout.strip()}")
        except Exception as e:
            self.log_deployment("❌ Docker not found", "WARNING")
        
        # Check if critical prerequisites are met
        critical_passed = prerequisites["python"] and prerequisites["node"]
        
        if critical_passed:
            self.log_deployment("✅ Critical prerequisites met")
            return True
        else:
            self.log_deployment("❌ Critical prerequisites missing", "ERROR")
            return False
    
    def install_dependencies(self) -> bool:
        """Install project dependencies"""
        self.log_deployment("📦 Installing dependencies...")
        
        try:
            # Install Python dependencies
            requirements_file = self.project_root / "requirements.txt"
            if requirements_file.exists():
                self.log_deployment("Installing Python dependencies...")
                result = subprocess.run([
                    "pip", "install", "-r", str(requirements_file)
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.log_deployment("✅ Python dependencies installed")
                else:
                    self.log_deployment(f"❌ Python dependencies failed: {result.stderr}", "ERROR")
                    return False
            else:
                self.log_deployment("❌ requirements.txt not found", "ERROR")
                return False
            
            # Check if package.json exists for Node dependencies
            package_json = self.project_root / "package.json"
            if package_json.exists():
                self.log_deployment("Installing Node.js dependencies...")
                result = subprocess.run(["npm", "install"], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.log_deployment("✅ Node.js dependencies installed")
                else:
                    self.log_deployment(f"❌ Node.js dependencies failed: {result.stderr}", "ERROR")
                    return False
            
            return True
            
        except Exception as e:
            self.log_deployment(f"❌ Dependency installation failed: {e}", "ERROR")
            return False
    
    def setup_environment(self) -> bool:
        """Setup environment configuration"""
        self.log_deployment("⚙️ Setting up environment...")
        
        try:
            # Check .env file
            env_file = self.project_root / ".env"
            env_example = self.project_root / ".env.example"
            
            if not env_file.exists() and env_example.exists():
                self.log_deployment("Creating .env file from example...")
                shutil.copy2(env_example, env_file)
                self.log_deployment("✅ .env file created")
            
            # Create necessary directories
            directories = ["data", "logs", "deployment"]
            for dir_name in directories:
                dir_path = self.project_root / dir_name
                dir_path.mkdir(exist_ok=True)
                gitkeep = dir_path / ".gitkeep"
                if not gitkeep.exists():
                    gitkeep.touch()
                self.log_deployment(f"✅ {dir_name}/ directory ready")
            
            return True
            
        except Exception as e:
            self.log_deployment(f"❌ Environment setup failed: {e}", "ERROR")
            return False
    
    def deploy_firebase_functions(self) -> bool:
        """Deploy Firebase Functions"""
        self.log_deployment("🔥 Deploying Firebase Functions...")
        
        try:
            # Check if firebase.json exists
            firebase_config = self.project_root / "firebase.json"
            if not firebase_config.exists():
                self.log_deployment("Creating Firebase configuration...")
                firebase_config_content = {
                    "functions": {
                        "source": "functions",
                        "runtime": "python311"
                    },
                    "hosting": {
                        "public": "web",
                        "ignore": ["firebase.json", "**/.*", "**/node_modules/**"]
                    }
                }
                
                with open(firebase_config, 'w') as f:
                    json.dump(firebase_config_content, f, indent=2)
                self.log_deployment("✅ Firebase configuration created")
            
            # Deploy functions
            self.log_deployment("Deploying to Firebase...")
            result = subprocess.run([
                "firebase", "deploy", "--only", "functions"
            ], capture_output=True, text=True, cwd=str(self.project_root))
            
            if result.returncode == 0:
                self.log_deployment("✅ Firebase Functions deployed")
                return True
            else:
                self.log_deployment(f"❌ Firebase deployment failed: {result.stderr}", "ERROR")
                return False
                
        except Exception as e:
            self.log_deployment(f"❌ Firebase deployment failed: {e}", "ERROR")
            return False
    
    def deploy_web_hosting(self) -> bool:
        """Deploy web hosting"""
        self.log_deployment("🌐 Deploying web hosting...")
        
        try:
            # Deploy hosting
            result = subprocess.run([
                "firebase", "deploy", "--only", "hosting"
            ], capture_output=True, text=True, cwd=str(self.project_root))
            
            if result.returncode == 0:
                self.log_deployment("✅ Web hosting deployed")
                return True
            else:
                self.log_deployment(f"❌ Web hosting deployment failed: {result.stderr}", "ERROR")
                return False
                
        except Exception as e:
            self.log_deployment(f"❌ Web hosting deployment failed: {e}", "ERROR")
            return False
    
    def setup_docker(self) -> bool:
        """Setup Docker deployment"""
        self.log_deployment("🐳 Setting up Docker...")
        
        try:
            # Check if Dockerfile exists
            dockerfile = self.project_root / "Dockerfile"
            if not dockerfile.exists():
                self.log_deployment("Creating Dockerfile...")
                dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    nodejs \\
    npm \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install Node.js dependencies if package.json exists
RUN if [ -f package.json ]; then npm install; fi

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "scripts.pipeline"]
"""
                with open(dockerfile, 'w') as f:
                    f.write(dockerfile_content)
                self.log_deployment("✅ Dockerfile created")
            
            # Check if docker-compose.yml exists
            compose_file = self.project_root / "docker-compose.yml"
            if not compose_file.exists():
                self.log_deployment("Creating docker-compose.yml...")
                compose_content = """version: '3.8'

services:
  cpr-nfl:
    build: .
    ports:
      - "8080:8080"
    environment:
      - ENVIRONMENT=production
      - FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
"""
                with open(compose_file, 'w') as f:
                    f.write(compose_content)
                self.log_deployment("✅ docker-compose.yml created")
            
            return True
            
        except Exception as e:
            self.log_deployment(f"❌ Docker setup failed: {e}", "ERROR")
            return False
    
    def run_tests(self) -> bool:
        """Run deployment tests"""
        self.log_deployment("🧪 Running deployment tests...")
        
        try:
            test_script = self.project_root / "scripts" / "test.py"
            if test_script.exists():
                result = subprocess.run([
                    "python", str(test_script), "--test", "all"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.log_deployment("✅ Deployment tests passed")
                    return True
                else:
                    self.log_deployment(f"❌ Deployment tests failed: {result.stderr}", "ERROR")
                    return False
            else:
                self.log_deployment("⚠️ Test script not found, skipping tests")
                return True
                
        except Exception as e:
            self.log_deployment(f"❌ Deployment tests failed: {e}", "ERROR")
            return False
    
    def create_deployment_backup(self) -> bool:
        """Create deployment backup"""
        self.log_deployment("💾 Creating deployment backup...")
        
        try:
            backup_dir = self.project_root / "deployment" / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"deployment_backup_{timestamp}.json"
            
            backup_data = {
                "deployment_time": datetime.now().isoformat(),
                "environment": self.environment,
                "deployment_log": self.deployment_log,
                "project_structure": self.get_project_structure()
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            self.log_deployment(f"✅ Backup created: {backup_file}")
            return True
            
        except Exception as e:
            self.log_deployment(f"❌ Backup creation failed: {e}", "ERROR")
            return False
    
    def get_project_structure(self) -> dict:
        """Get current project structure"""
        structure = {}
        
        for item in self.project_root.rglob("*"):
            if item.is_file():
                relative_path = str(item.relative_to(self.project_root))
                structure[relative_path] = {
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                }
        
        return structure
    
    async def deploy_all(self, skip_tests: bool = False) -> dict:
        """Execute full deployment"""
        self.log_deployment("🚀 Starting full deployment...")
        
        start_time = datetime.now()
        deployment_steps = []
        
        # Step 1: Check prerequisites
        if not self.check_prerequisites():
            return {"success": False, "error": "Prerequisites not met"}
        
        # Step 2: Install dependencies
        if not self.install_dependencies():
            return {"success": False, "error": "Dependency installation failed"}
        
        # Step 3: Setup environment
        if not self.setup_environment():
            return {"success": False, "error": "Environment setup failed"}
        
        # Step 4: Setup Docker
        if not self.setup_docker():
            return {"success": False, "error": "Docker setup failed"}
        
        # Step 5: Run tests (unless skipped)
        if not skip_tests:
            if not self.run_tests():
                return {"success": False, "error": "Deployment tests failed"}
        
        # Step 6: Deploy Firebase Functions
        if not self.deploy_firebase_functions():
            return {"success": False, "error": "Firebase Functions deployment failed"}
        
        # Step 7: Deploy web hosting
        if not self.deploy_web_hosting():
            return {"success": False, "error": "Web hosting deployment failed"}
        
        # Step 8: Create backup
        self.create_deployment_backup()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        deployment_summary = {
            "success": True,
            "environment": self.environment,
            "duration_seconds": duration,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "deployment_log": self.deployment_log
        }
        
        self.log_deployment("✅ Full deployment completed successfully!")
        return deployment_summary
    
    def print_deployment_report(self, summary: dict):
        """Print deployment report"""
        print("\n" + "="*60)
        print("🚀 CPR-NFL DEPLOYMENT REPORT")
        print("="*60)
        
        if summary["success"]:
            print(f"🟢 DEPLOYMENT SUCCESSFUL")
            print(f"   Environment: {summary['environment']}")
            print(f"   Duration: {summary.get('duration_seconds', 0):.2f}s")
            if 'start_time' in summary:
                print(f"   Start Time: {summary['start_time']}")
                print(f"   End Time: {summary['end_time']}")
            if 'step' in summary:
                print(f"   Step: {summary['step']}")
        else:
            print(f"🔴 DEPLOYMENT FAILED")
            print(f"   Error: {summary.get('error', 'Unknown error')}")
        
        print(f"\n📋 DEPLOYMENT LOG:")
        for entry in summary.get("deployment_log", [])[-10:]:  # Show last 10 entries
            level_icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(entry["level"], "ℹ️")
            print(f"   {level_icon} {entry['timestamp']}: {entry['message']}")
        
        print("="*60)

async def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy CPR-NFL system")
    parser.add_argument("--environment", choices=["development", "staging", "production"], 
                       default="development", help="Deployment environment")
    parser.add_argument("--skip-tests", action="store_true", 
                       help="Skip deployment tests")
    parser.add_argument("--step", choices=[
        "prereqs", "deps", "env", "docker", "test", "firebase", "hosting", "all"
    ], default="all", help="Specific deployment step")
    parser.add_argument("--output", help="Output file for deployment report")
    
    args = parser.parse_args()
    
    # Initialize deployment manager
    deployer = DeploymentManager(args.environment)
    
    # Run deployment
    if args.step == "all":
        summary = await deployer.deploy_all(skip_tests=args.skip_tests)
    else:
        step_map = {
            "prereqs": deployer.check_prerequisites,
            "deps": deployer.install_dependencies,
            "env": deployer.setup_environment,
            "docker": deployer.setup_docker,
            "test": deployer.run_tests,
            "firebase": deployer.deploy_firebase_functions,
            "hosting": deployer.deploy_web_hosting
        }
        
        if args.step in step_map:
            result = step_map[args.step]()
            summary = {
                "success": result,
                "environment": args.environment,
                "step": args.step,
                "deployment_log": deployer.deployment_log
            }
        else:
            logger.error(f"Unknown deployment step: {args.step}")
            return
    
    # Print report
    deployer.print_deployment_report(summary)
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"💾 Deployment report saved to {args.output}")
    
    # Exit with appropriate code
    exit_code = 0 if summary["success"] else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
