"""
Machine Learning engine for predictive error prevention and intelligent system optimization.
"""

import asyncio
import json
import logging
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import statistics

from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn


class PredictionType(Enum):
    """Types of predictions the ML engine can make."""
    ERROR_PROBABILITY = "error_probability"
    PERFORMANCE_DEGRADATION = "performance_degradation" 
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    USER_BEHAVIOR = "user_behavior"
    FAILURE_CASCADE = "failure_cascade"
    OPTIMAL_CONFIGURATION = "optimal_configuration"
    ANOMALY_DETECTION = "anomaly_detection"


class ModelType(Enum):
    """Types of ML models available."""
    LINEAR_REGRESSION = "linear_regression"
    LOGISTIC_REGRESSION = "logistic_regression"
    DECISION_TREE = "decision_tree"
    RANDOM_FOREST = "random_forest"
    NEURAL_NETWORK = "neural_network"
    CLUSTERING = "clustering"
    TIME_SERIES = "time_series"
    ENSEMBLE = "ensemble"


@dataclass
class TrainingData:
    """Training data for ML models."""
    features: np.ndarray
    labels: np.ndarray
    feature_names: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PredictionResult:
    """Result of a ML prediction."""
    prediction: Union[float, int, str, List]
    confidence: float
    model_used: str
    features_used: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ModelPerformance:
    """Performance metrics for ML models."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_time: float
    prediction_time: float
    data_size: int
    last_updated: datetime = field(default_factory=datetime.now)


class PredictionModel:
    """Base class for ML prediction models."""
    
    def __init__(self, model_type: ModelType, prediction_type: PredictionType):
        self.model_type = model_type
        self.prediction_type = prediction_type
        self.model = None
        self.is_trained = False
        self.performance = None
        self.feature_importance = {}
        self.training_history = []
        
    def train(self, data: TrainingData) -> ModelPerformance:
        """Train the model with provided data."""
        raise NotImplementedError
    
    def predict(self, features: np.ndarray) -> PredictionResult:
        """Make prediction with the trained model."""
        raise NotImplementedError
    
    def update(self, new_data: TrainingData) -> ModelPerformance:
        """Update model with new data (online learning)."""
        raise NotImplementedError
    
    def save(self, path: Path):
        """Save model to disk."""
        model_data = {
            'model': self.model,
            'model_type': self.model_type.value,
            'prediction_type': self.prediction_type.value,
            'is_trained': self.is_trained,
            'performance': self.performance,
            'feature_importance': self.feature_importance,
            'training_history': self.training_history
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load(self, path: Path):
        """Load model from disk."""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.is_trained = model_data['is_trained']
        self.performance = model_data.get('performance')
        self.feature_importance = model_data.get('feature_importance', {})
        self.training_history = model_data.get('training_history', [])


class ErrorPredictionModel(PredictionModel):
    """Specialized model for predicting error probability."""
    
    def __init__(self):
        super().__init__(ModelType.LOGISTIC_REGRESSION, PredictionType.ERROR_PROBABILITY)
        self.threshold = 0.5
        
    def train(self, data: TrainingData) -> ModelPerformance:
        """Train error prediction model."""
        start_time = datetime.now()
        
        # Simple logistic regression implementation
        # In a real implementation, you'd use scikit-learn or similar
        X, y = data.features, data.labels
        
        # Placeholder training logic
        # This would be replaced with actual ML library calls
        self.model = {
            'weights': np.random.random(X.shape[1]),
            'bias': np.random.random(),
            'feature_names': data.feature_names
        }
        
        self.is_trained = True
        training_time = (datetime.now() - start_time).total_seconds()
        
        # Calculate performance metrics (simplified)
        predictions = self._sigmoid(X @ self.model['weights'] + self.model['bias'])
        predicted_labels = (predictions > self.threshold).astype(int)
        
        accuracy = np.mean(predicted_labels == y)
        
        self.performance = ModelPerformance(
            accuracy=accuracy,
            precision=accuracy,  # Simplified
            recall=accuracy,     # Simplified
            f1_score=accuracy,   # Simplified
            training_time=training_time,
            prediction_time=0.001,  # Estimate
            data_size=len(y)
        )
        
        self.training_history.append({
            'timestamp': start_time,
            'data_size': len(y),
            'accuracy': accuracy
        })
        
        return self.performance
    
    def predict(self, features: np.ndarray) -> PredictionResult:
        """Predict error probability."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        start_time = datetime.now()
        
        # Make prediction
        logits = features @ self.model['weights'] + self.model['bias']
        probability = self._sigmoid(logits)
        
        prediction_time = (datetime.now() - start_time).total_seconds()
        
        return PredictionResult(
            prediction=float(probability),
            confidence=abs(probability - 0.5) * 2,  # Distance from decision boundary
            model_used=f"{self.model_type.value}_{self.prediction_type.value}",
            features_used=self.model['feature_names'],
            metadata={
                'prediction_time': prediction_time,
                'threshold': self.threshold
            }
        )
    
    def _sigmoid(self, x):
        """Sigmoid activation function."""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))  # Clip to prevent overflow


class PerformancePredictionModel(PredictionModel):
    """Model for predicting performance degradation."""
    
    def __init__(self):
        super().__init__(ModelType.TIME_SERIES, PredictionType.PERFORMANCE_DEGRADATION)
        self.window_size = 10
        
    def train(self, data: TrainingData) -> ModelPerformance:
        """Train performance prediction model."""
        start_time = datetime.now()
        
        # Simple moving average model for time series prediction
        X, y = data.features, data.labels
        
        self.model = {
            'baseline_performance': np.mean(y),
            'trend_coefficient': np.polyfit(range(len(y)), y, 1)[0],
            'feature_names': data.feature_names,
            'history': y[-self.window_size:].tolist()
        }
        
        self.is_trained = True
        training_time = (datetime.now() - start_time).total_seconds()
        
        # Simple performance calculation
        predictions = [self.model['baseline_performance']] * len(y)
        mse = np.mean((predictions - y) ** 2)
        accuracy = max(0, 1 - (mse / np.var(y))) if np.var(y) > 0 else 0
        
        self.performance = ModelPerformance(
            accuracy=accuracy,
            precision=accuracy,
            recall=accuracy,
            f1_score=accuracy,
            training_time=training_time,
            prediction_time=0.001,
            data_size=len(y)
        )
        
        return self.performance
    
    def predict(self, features: np.ndarray) -> PredictionResult:
        """Predict performance degradation."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        start_time = datetime.now()
        
        # Simple prediction based on trend and recent history
        recent_avg = np.mean(self.model['history'])
        trend_adjustment = self.model['trend_coefficient'] * len(self.model['history'])
        prediction = recent_avg + trend_adjustment
        
        # Calculate confidence based on variance in recent history
        variance = np.var(self.model['history'])
        confidence = max(0, min(1, 1 - (variance / self.model['baseline_performance']))) if self.model['baseline_performance'] > 0 else 0.5
        
        prediction_time = (datetime.now() - start_time).total_seconds()
        
        return PredictionResult(
            prediction=float(prediction),
            confidence=confidence,
            model_used=f"{self.model_type.value}_{self.prediction_type.value}",
            features_used=self.model['feature_names'],
            metadata={
                'prediction_time': prediction_time,
                'baseline_performance': self.model['baseline_performance'],
                'trend': self.model['trend_coefficient']
            }
        )


class LearningSystem:
    """Automated learning system that manages multiple models and continuous improvement."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.analytics.learning_system")
        
        # Model management
        self.models: Dict[str, PredictionModel] = {}
        self.active_models: Dict[PredictionType, str] = {}
        
        # Learning configuration
        self.auto_retrain = True
        self.retrain_threshold = 0.1  # Retrain if accuracy drops by 10%
        self.min_training_samples = 100
        self.max_training_samples = 10000
        
        # Data management
        self.training_data_cache: Dict[PredictionType, List[TrainingData]] = {}
        self.prediction_feedback: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.model_performance_history = {}
        
        # Initialize default models
        self._initialize_default_models()
    
    def _initialize_default_models(self):
        """Initialize default prediction models."""
        # Error prediction model
        error_model = ErrorPredictionModel()
        self.add_model("error_predictor", error_model)
        self.active_models[PredictionType.ERROR_PROBABILITY] = "error_predictor"
        
        # Performance prediction model
        perf_model = PerformancePredictionModel()
        self.add_model("performance_predictor", perf_model)
        self.active_models[PredictionType.PERFORMANCE_DEGRADATION] = "performance_predictor"
    
    def add_model(self, model_id: str, model: PredictionModel):
        """Add a new model to the system."""
        self.models[model_id] = model
        self.logger.info(f"Added model: {model_id} ({model.model_type.value})")
    
    def train_model(self, model_id: str, data: TrainingData) -> Optional[ModelPerformance]:
        """Train a specific model."""
        if model_id not in self.models:
            self.logger.error(f"Model {model_id} not found")
            return None
        
        model = self.models[model_id]
        
        try:
            self.console.print(f"[cyan]Training model: {model_id}[/cyan]")
            
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=self.console,
            ) as progress:
                
                task = progress.add_task("Training...", total=None)
                performance = model.train(data)
                progress.update(task, completed=True)
            
            # Cache training data
            if model.prediction_type not in self.training_data_cache:
                self.training_data_cache[model.prediction_type] = []
            
            self.training_data_cache[model.prediction_type].append(data)
            
            # Keep only recent training data
            if len(self.training_data_cache[model.prediction_type]) > 100:
                self.training_data_cache[model.prediction_type] = self.training_data_cache[model.prediction_type][-100:]
            
            # Track performance history
            if model_id not in self.model_performance_history:
                self.model_performance_history[model_id] = []
            
            self.model_performance_history[model_id].append(performance)
            
            self.console.print(f"[green]✓ Model {model_id} trained successfully (accuracy: {performance.accuracy:.3f})[/green]")
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Failed to train model {model_id}: {e}")
            self.console.print(f"[red]✗ Failed to train model {model_id}: {e}[/red]")
            return None
    
    def predict(self, prediction_type: PredictionType, features: np.ndarray, model_id: Optional[str] = None) -> Optional[PredictionResult]:
        """Make a prediction using the appropriate model."""
        # Determine which model to use
        if model_id:
            if model_id not in self.models:
                self.logger.error(f"Model {model_id} not found")
                return None
            model = self.models[model_id]
        else:
            if prediction_type not in self.active_models:
                self.logger.error(f"No active model for prediction type {prediction_type.value}")
                return None
            model_id = self.active_models[prediction_type]
            model = self.models[model_id]
        
        try:
            result = model.predict(features)
            
            self.logger.info(f"Prediction made: {prediction_type.value} -> {result.prediction} (confidence: {result.confidence:.3f})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Prediction failed for {model_id}: {e}")
            return None
    
    def add_feedback(self, prediction_result: PredictionResult, actual_outcome: Any):
        """Add feedback for improving model accuracy."""
        feedback = {
            'prediction': prediction_result,
            'actual_outcome': actual_outcome,
            'timestamp': datetime.now(),
            'model_used': prediction_result.model_used
        }
        
        self.prediction_feedback.append(feedback)
        
        # Keep only recent feedback
        if len(self.prediction_feedback) > 1000:
            self.prediction_feedback = self.prediction_feedback[-1000:]
        
        # Check if we need to retrain
        if self.auto_retrain:
            self._check_retrain_needed(prediction_result.model_used)
    
    def _check_retrain_needed(self, model_id: str):
        """Check if a model needs retraining based on recent performance."""
        if model_id not in self.models:
            return
        
        # Get recent feedback for this model
        recent_feedback = [
            f for f in self.prediction_feedback[-100:]  # Last 100 predictions
            if f['prediction'].model_used == model_id
        ]
        
        if len(recent_feedback) < 20:  # Need enough samples
            return
        
        # Calculate recent accuracy
        correct_predictions = 0
        for feedback in recent_feedback:
            prediction = feedback['prediction'].prediction
            actual = feedback['actual_outcome']
            
            # Simple accuracy check (this would be more sophisticated in practice)
            if isinstance(prediction, float) and isinstance(actual, (int, float)):
                error = abs(prediction - actual)
                relative_error = error / max(abs(actual), 1)
                if relative_error < 0.1:  # Within 10%
                    correct_predictions += 1
        
        recent_accuracy = correct_predictions / len(recent_feedback)
        
        # Compare with historical performance
        model = self.models[model_id]
        if model.performance and recent_accuracy < model.performance.accuracy - self.retrain_threshold:
            self.logger.warning(f"Model {model_id} performance degraded: {recent_accuracy:.3f} vs {model.performance.accuracy:.3f}")
            self._schedule_retrain(model_id)
    
    def _schedule_retrain(self, model_id: str):
        """Schedule a model for retraining."""
        self.logger.info(f"Scheduling retrain for model: {model_id}")
        # In a real implementation, this would queue the retraining task
        # For now, we'll just log it
    
    def get_model_insights(self, model_id: str) -> Dict[str, Any]:
        """Get insights about a specific model."""
        if model_id not in self.models:
            return {}
        
        model = self.models[model_id]
        insights = {
            'model_type': model.model_type.value,
            'prediction_type': model.prediction_type.value,
            'is_trained': model.is_trained,
            'performance': model.performance.__dict__ if model.performance else None,
            'feature_importance': model.feature_importance,
            'training_history_count': len(model.training_history)
        }
        
        # Add performance history
        if model_id in self.model_performance_history:
            history = self.model_performance_history[model_id]
            insights['performance_trend'] = [p.accuracy for p in history[-10:]]
        
        # Add recent feedback accuracy
        recent_feedback = [
            f for f in self.prediction_feedback[-50:]
            if f['prediction'].model_used == model_id
        ]
        
        if recent_feedback:
            insights['recent_feedback_count'] = len(recent_feedback)
            # Calculate recent accuracy (simplified)
            insights['recent_accuracy_estimate'] = 0.8  # Placeholder
        
        return insights
    
    def export_models(self, directory: Path):
        """Export all trained models to disk."""
        directory.mkdir(parents=True, exist_ok=True)
        
        for model_id, model in self.models.items():
            if model.is_trained:
                model_path = directory / f"{model_id}.pkl"
                try:
                    model.save(model_path)
                    self.logger.info(f"Exported model {model_id} to {model_path}")
                except Exception as e:
                    self.logger.error(f"Failed to export model {model_id}: {e}")
    
    def import_models(self, directory: Path):
        """Import models from disk."""
        for model_file in directory.glob("*.pkl"):
            model_id = model_file.stem
            
            try:
                # Create appropriate model instance based on name
                if "error" in model_id.lower():
                    model = ErrorPredictionModel()
                elif "performance" in model_id.lower():
                    model = PerformancePredictionModel()
                else:
                    continue  # Skip unknown models
                
                model.load(model_file)
                self.models[model_id] = model
                
                self.logger.info(f"Imported model {model_id} from {model_file}")
                
            except Exception as e:
                self.logger.error(f"Failed to import model from {model_file}: {e}")


class MLEngine:
    """Main ML engine that orchestrates learning systems and provides high-level ML capabilities."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.analytics.ml_engine")
        
        # Core components
        self.learning_system = LearningSystem(console)
        
        # Feature extraction
        self.feature_extractors: Dict[str, Callable] = {}
        
        # Data preprocessing
        self.preprocessors: Dict[str, Callable] = {}
        
        # Real-time prediction cache
        self.prediction_cache: Dict[str, Tuple[PredictionResult, datetime]] = {}
        self.cache_ttl = timedelta(minutes=5)
        
        # Initialize feature extractors
        self._initialize_feature_extractors()
    
    def _initialize_feature_extractors(self):
        """Initialize feature extraction functions."""
        
        def extract_error_features(context: Dict[str, Any]) -> np.ndarray:
            """Extract features for error prediction."""
            features = []
            
            # System metrics
            features.append(context.get('cpu_usage', 0.0))
            features.append(context.get('memory_usage', 0.0))
            features.append(context.get('error_count_last_hour', 0))
            features.append(context.get('response_time_avg', 0.0))
            features.append(context.get('active_connections', 0))
            
            # Provider metrics  
            features.append(context.get('provider_error_rate', 0.0))
            features.append(context.get('provider_latency', 0.0))
            
            # MCP metrics
            features.append(context.get('mcp_servers_active', 0))
            features.append(context.get('mcp_error_rate', 0.0))
            
            return np.array(features)
        
        def extract_performance_features(context: Dict[str, Any]) -> np.ndarray:
            """Extract features for performance prediction."""
            features = []
            
            # Historical performance
            perf_history = context.get('performance_history', [])
            if len(perf_history) >= 5:
                features.extend(perf_history[-5:])  # Last 5 measurements
            else:
                features.extend(perf_history + [0] * (5 - len(perf_history)))
            
            # System load
            features.append(context.get('system_load', 0.0))
            features.append(context.get('concurrent_requests', 0))
            features.append(context.get('queue_length', 0))
            
            return np.array(features)
        
        self.feature_extractors['error_prediction'] = extract_error_features
        self.feature_extractors['performance_prediction'] = extract_performance_features
    
    async def predict_error_probability(self, context: Dict[str, Any]) -> Optional[PredictionResult]:
        """Predict probability of error occurrence."""
        cache_key = f"error_probability_{hash(str(context))}"
        
        # Check cache
        if cache_key in self.prediction_cache:
            result, timestamp = self.prediction_cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return result
        
        # Extract features
        features = self.feature_extractors['error_prediction'](context)
        
        # Make prediction
        result = self.learning_system.predict(
            PredictionType.ERROR_PROBABILITY,
            features.reshape(1, -1)
        )
        
        # Cache result
        if result:
            self.prediction_cache[cache_key] = (result, datetime.now())
        
        return result
    
    async def predict_performance_degradation(self, context: Dict[str, Any]) -> Optional[PredictionResult]:
        """Predict performance degradation."""
        cache_key = f"performance_degradation_{hash(str(context))}"
        
        # Check cache
        if cache_key in self.prediction_cache:
            result, timestamp = self.prediction_cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return result
        
        # Extract features
        features = self.feature_extractors['performance_prediction'](context)
        
        # Make prediction
        result = self.learning_system.predict(
            PredictionType.PERFORMANCE_DEGRADATION,
            features.reshape(1, -1)
        )
        
        # Cache result
        if result:
            self.prediction_cache[cache_key] = (result, datetime.now())
        
        return result
    
    def train_error_prediction_model(self, historical_data: List[Dict[str, Any]]) -> bool:
        """Train the error prediction model with historical data."""
        try:
            self.console.print("[cyan]Preparing error prediction training data...[/cyan]")
            
            # Extract features and labels
            features_list = []
            labels_list = []
            
            for record in historical_data:
                features = self.feature_extractors['error_prediction'](record)
                label = 1 if record.get('had_error', False) else 0
                
                features_list.append(features)
                labels_list.append(label)
            
            # Create training data
            training_data = TrainingData(
                features=np.array(features_list),
                labels=np.array(labels_list),
                feature_names=[
                    'cpu_usage', 'memory_usage', 'error_count_last_hour',
                    'response_time_avg', 'active_connections', 'provider_error_rate',
                    'provider_latency', 'mcp_servers_active', 'mcp_error_rate'
                ]
            )
            
            # Train model
            performance = self.learning_system.train_model("error_predictor", training_data)
            
            return performance is not None
            
        except Exception as e:
            self.logger.error(f"Error training prediction model failed: {e}")
            self.console.print(f"[red]✗ Error prediction training failed: {e}[/red]")
            return False
    
    def train_performance_prediction_model(self, historical_data: List[Dict[str, Any]]) -> bool:
        """Train the performance prediction model with historical data."""
        try:
            self.console.print("[cyan]Preparing performance prediction training data...[/cyan]")
            
            # Extract features and labels
            features_list = []
            labels_list = []
            
            for record in historical_data:
                features = self.feature_extractors['performance_prediction'](record)
                label = record.get('performance_score', 0.0)
                
                features_list.append(features)
                labels_list.append(label)
            
            # Create training data
            training_data = TrainingData(
                features=np.array(features_list),
                labels=np.array(labels_list),
                feature_names=[
                    'perf_t-5', 'perf_t-4', 'perf_t-3', 'perf_t-2', 'perf_t-1',
                    'system_load', 'concurrent_requests', 'queue_length'
                ]
            )
            
            # Train model
            performance = self.learning_system.train_model("performance_predictor", training_data)
            
            return performance is not None
            
        except Exception as e:
            self.logger.error(f"Performance prediction training failed: {e}")
            self.console.print(f"[red]✗ Performance prediction training failed: {e}[/red]")
            return False
    
    def get_ml_insights(self) -> Dict[str, Any]:
        """Get comprehensive ML system insights."""
        insights = {
            'models': {},
            'predictions_made': len(self.prediction_cache),
            'cache_hit_ratio': 0.0,  # Would track this in practice
            'learning_system_status': 'active'
        }
        
        # Get insights for each model
        for model_id in self.learning_system.models:
            insights['models'][model_id] = self.learning_system.get_model_insights(model_id)
        
        return insights
    
    def cleanup_cache(self):
        """Clean up expired prediction cache entries."""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.prediction_cache.items()
            if now - timestamp > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.prediction_cache[key]
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")