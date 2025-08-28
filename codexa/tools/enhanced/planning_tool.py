"""
Planning Tool - Handles task planning, execution strategies, and workflow management for Codexa
"""

import json
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolStatus


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task status types"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a planned task"""
    id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    estimated_time: int = 0  # minutes
    actual_time: int = 0  # minutes
    dependencies: List[str] = None
    tags: List[str] = None
    created_at: float = None
    started_at: float = None
    completed_at: float = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class Plan:
    """Represents an execution plan"""
    id: str
    name: str
    description: str
    tasks: List[Task]
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class PlanningTool(Tool):
    """Tool for task planning and execution strategy management"""
    
    def __init__(self):
        super().__init__()
        self.plans: Dict[str, Plan] = {}
        self.active_plan: Optional[str] = None
        self.task_counter = 0
        self.plan_counter = 0
        self._load_saved_plans()
    
    @property
    def name(self) -> str:
        return "planning"
    
    @property
    def description(self) -> str:
        return "Handles task planning, execution strategies, and workflow management"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def capabilities(self) -> List[str]:
        return [
            "create_plan",
            "add_task",
            "update_task",
            "remove_task",
            "list_plans",
            "list_tasks",
            "set_active_plan",
            "get_plan_status",
            "dependency_analysis",
            "time_estimation",
            "priority_management",
            "execution_strategy",
            "progress_tracking",
            "plan_export",
            "plan_import"
        ]
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the planning request"""
        request_lower = request.lower()
        
        # High confidence for explicit planning requests
        if any(word in request_lower for word in [
            'plan', 'planning', 'task', 'schedule', 'strategy',
            'create plan', 'add task', 'execution plan'
        ]):
            return 0.9
            
        # Medium confidence for workflow requests
        if any(word in request_lower for word in [
            'workflow', 'organize', 'manage', 'priority',
            'dependencies', 'timeline', 'roadmap'
        ]):
            return 0.7
            
        # Lower confidence for general organization requests
        if any(word in request_lower for word in [
            'organize', 'structure', 'break down', 'steps'
        ]):
            return 0.4
            
        return 0.0
    
    def execute(self, request: str, context: ToolContext) -> ToolResult:
        """Execute planning operation based on request"""
        try:
            operation, params = self._parse_planning_request(request)
            
            # Route to appropriate handler
            handlers = {
                'create_plan': self._create_plan,
                'add_task': self._add_task,
                'update_task': self._update_task,
                'remove_task': self._remove_task,
                'list_plans': self._list_plans,
                'list_tasks': self._list_tasks,
                'set_active': self._set_active_plan,
                'get_status': self._get_plan_status,
                'analyze_dependencies': self._analyze_dependencies,
                'estimate_time': self._estimate_time,
                'update_priority': self._update_priority,
                'track_progress': self._track_progress,
                'export_plan': self._export_plan,
                'import_plan': self._import_plan
            }
            
            if operation not in handlers:
                return ToolResult(
                    success=False,
                    data={'error': f'Unknown planning operation: {operation}'},
                    message=f"Planning operation '{operation}' not supported",
                    status=ToolStatus.ERROR
                )
            
            result = handlers[operation](params, context)
            
            return ToolResult(
                success=True,
                data=result,
                message=f"Planning {operation} completed successfully",
                status=ToolStatus.SUCCESS
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                data={'error': str(e)},
                message=f"Planning operation failed: {str(e)}",
                status=ToolStatus.ERROR
            )
    
    def _parse_planning_request(self, request: str) -> tuple[str, Dict[str, Any]]:
        """Parse planning request to extract operation and parameters"""
        request_lower = request.lower()
        params = {}
        
        # Determine operation
        if any(word in request_lower for word in ['create plan', 'new plan']):
            operation = 'create_plan'
            # Extract plan name
            import re
            name_match = re.search(r'(?:plan|named?)\s+["\']?([^"\']+)["\']?', request)
            if name_match:
                params['name'] = name_match.group(1).strip()
        elif any(word in request_lower for word in ['add task', 'new task', 'create task']):
            operation = 'add_task'
            # Extract task details
            params.update(self._extract_task_params(request))
        elif 'update task' in request_lower:
            operation = 'update_task'
            params.update(self._extract_task_params(request))
        elif any(word in request_lower for word in ['remove task', 'delete task']):
            operation = 'remove_task'
            # Extract task ID
            import re
            id_match = re.search(r'task\s+["\']?([^"\']+)["\']?', request)
            if id_match:
                params['task_id'] = id_match.group(1).strip()
        elif 'list plans' in request_lower:
            operation = 'list_plans'
        elif 'list tasks' in request_lower:
            operation = 'list_tasks'
        elif any(word in request_lower for word in ['set active', 'active plan']):
            operation = 'set_active'
            # Extract plan ID
            import re
            id_match = re.search(r'(?:plan|set active)\s+["\']?([^"\']+)["\']?', request)
            if id_match:
                params['plan_id'] = id_match.group(1).strip()
        elif any(word in request_lower for word in ['plan status', 'status']):
            operation = 'get_status'
        elif 'dependencies' in request_lower:
            operation = 'analyze_dependencies'
        elif 'estimate' in request_lower:
            operation = 'estimate_time'
        elif 'priority' in request_lower:
            operation = 'update_priority'
        elif 'progress' in request_lower:
            operation = 'track_progress'
        elif 'export' in request_lower:
            operation = 'export_plan'
        elif 'import' in request_lower:
            operation = 'import_plan'
        else:
            operation = 'list_plans'  # Default
        
        return operation, params
    
    def _extract_task_params(self, request: str) -> Dict[str, Any]:
        """Extract task parameters from request"""
        params = {}
        
        # Extract task title
        import re
        title_match = re.search(r'(?:task|titled?)\s+["\']([^"\']+)["\']', request)
        if title_match:
            params['title'] = title_match.group(1)
        
        # Extract description
        desc_match = re.search(r'description\s+["\']([^"\']+)["\']', request)
        if desc_match:
            params['description'] = desc_match.group(1)
        
        # Extract priority
        if 'high priority' in request.lower():
            params['priority'] = TaskPriority.HIGH
        elif 'critical priority' in request.lower():
            params['priority'] = TaskPriority.CRITICAL
        elif 'low priority' in request.lower():
            params['priority'] = TaskPriority.LOW
        else:
            params['priority'] = TaskPriority.MEDIUM
        
        # Extract estimated time
        time_match = re.search(r'(\d+)\s*(?:minutes?|mins?|hours?|hrs?)', request.lower())
        if time_match:
            time_value = int(time_match.group(1))
            time_unit = time_match.group(0).split()[-1]
            if 'hour' in time_unit or 'hr' in time_unit:
                params['estimated_time'] = time_value * 60
            else:
                params['estimated_time'] = time_value
        
        return params
    
    def _create_plan(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Create new execution plan"""
        name = params.get('name', f'Plan {self.plan_counter + 1}')
        description = params.get('description', f'Execution plan: {name}')
        
        plan_id = f'plan_{self.plan_counter}'
        self.plan_counter += 1
        
        plan = Plan(
            id=plan_id,
            name=name,
            description=description,
            tasks=[]
        )
        
        self.plans[plan_id] = plan
        self.active_plan = plan_id
        
        self._save_plans()
        
        return {
            'plan_created': plan_id,
            'name': name,
            'description': description,
            'created_at': plan.created_at,
            'active': True
        }
    
    def _add_task(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Add task to active plan"""
        if not self.active_plan or self.active_plan not in self.plans:
            return {'error': 'No active plan. Create a plan first.'}
        
        title = params.get('title', f'Task {self.task_counter + 1}')
        description = params.get('description', f'Task: {title}')
        priority = params.get('priority', TaskPriority.MEDIUM)
        estimated_time = params.get('estimated_time', 30)
        
        task_id = f'task_{self.task_counter}'
        self.task_counter += 1
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            status=TaskStatus.PENDING,
            estimated_time=estimated_time
        )
        
        self.plans[self.active_plan].tasks.append(task)
        self._save_plans()
        
        return {
            'task_added': task_id,
            'title': title,
            'priority': priority.name,
            'estimated_time': estimated_time,
            'plan': self.active_plan
        }
    
    def _update_task(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Update existing task"""
        task_id = params.get('task_id')
        if not task_id:
            return {'error': 'Task ID required'}
        
        # Find task
        task = None
        plan_id = None
        for pid, plan in self.plans.items():
            for t in plan.tasks:
                if t.id == task_id:
                    task = t
                    plan_id = pid
                    break
            if task:
                break
        
        if not task:
            return {'error': f'Task {task_id} not found'}
        
        # Update fields
        updated_fields = []
        if 'title' in params:
            task.title = params['title']
            updated_fields.append('title')
        if 'description' in params:
            task.description = params['description']
            updated_fields.append('description')
        if 'priority' in params:
            task.priority = params['priority']
            updated_fields.append('priority')
        if 'status' in params:
            task.status = params['status']
            updated_fields.append('status')
            if params['status'] == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = time.time()
            elif params['status'] == TaskStatus.COMPLETED and not task.completed_at:
                task.completed_at = time.time()
        
        self._save_plans()
        
        return {
            'task_updated': task_id,
            'updated_fields': updated_fields,
            'current_status': task.status.value,
            'plan': plan_id
        }
    
    def _remove_task(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Remove task from plan"""
        task_id = params.get('task_id')
        if not task_id:
            return {'error': 'Task ID required'}
        
        # Find and remove task
        for plan in self.plans.values():
            for i, task in enumerate(plan.tasks):
                if task.id == task_id:
                    removed_task = plan.tasks.pop(i)
                    self._save_plans()
                    return {
                        'task_removed': task_id,
                        'title': removed_task.title,
                        'plan': plan.id
                    }
        
        return {'error': f'Task {task_id} not found'}
    
    def _list_plans(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """List all plans"""
        plans_info = []
        
        for plan in self.plans.values():
            task_counts = {
                'total': len(plan.tasks),
                'completed': len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED]),
                'in_progress': len([t for t in plan.tasks if t.status == TaskStatus.IN_PROGRESS]),
                'pending': len([t for t in plan.tasks if t.status == TaskStatus.PENDING])
            }
            
            plans_info.append({
                'id': plan.id,
                'name': plan.name,
                'description': plan.description,
                'created_at': plan.created_at,
                'task_counts': task_counts,
                'active': plan.id == self.active_plan
            })
        
        return {
            'plans': plans_info,
            'total_plans': len(self.plans),
            'active_plan': self.active_plan
        }
    
    def _list_tasks(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """List tasks from active plan"""
        if not self.active_plan or self.active_plan not in self.plans:
            return {'error': 'No active plan'}
        
        plan = self.plans[self.active_plan]
        tasks_info = []
        
        for task in plan.tasks:
            tasks_info.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'priority': task.priority.name,
                'status': task.status.value,
                'estimated_time': task.estimated_time,
                'actual_time': task.actual_time,
                'dependencies': task.dependencies,
                'tags': task.tags,
                'created_at': task.created_at,
                'started_at': task.started_at,
                'completed_at': task.completed_at
            })
        
        return {
            'plan_id': plan.id,
            'plan_name': plan.name,
            'tasks': tasks_info,
            'total_tasks': len(tasks_info)
        }
    
    def _set_active_plan(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Set active plan"""
        plan_id = params.get('plan_id')
        if not plan_id or plan_id not in self.plans:
            return {'error': f'Plan {plan_id} not found'}
        
        self.active_plan = plan_id
        plan = self.plans[plan_id]
        
        return {
            'active_plan_set': plan_id,
            'name': plan.name,
            'task_count': len(plan.tasks)
        }
    
    def _get_plan_status(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Get plan status and progress"""
        if not self.active_plan or self.active_plan not in self.plans:
            return {'error': 'No active plan'}
        
        plan = self.plans[self.active_plan]
        
        # Calculate progress
        total_tasks = len(plan.tasks)
        if total_tasks == 0:
            return {
                'plan_id': plan.id,
                'name': plan.name,
                'total_tasks': 0,
                'progress': 0,
                'message': 'No tasks in plan'
            }
        
        completed = len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED])
        in_progress = len([t for t in plan.tasks if t.status == TaskStatus.IN_PROGRESS])
        pending = len([t for t in plan.tasks if t.status == TaskStatus.PENDING])
        blocked = len([t for t in plan.tasks if t.status == TaskStatus.BLOCKED])
        
        progress = (completed / total_tasks) * 100
        
        # Time estimates
        total_estimated = sum(t.estimated_time for t in plan.tasks)
        total_actual = sum(t.actual_time for t in plan.tasks)
        
        return {
            'plan_id': plan.id,
            'name': plan.name,
            'description': plan.description,
            'total_tasks': total_tasks,
            'progress_percent': round(progress, 1),
            'task_breakdown': {
                'completed': completed,
                'in_progress': in_progress,
                'pending': pending,
                'blocked': blocked
            },
            'time_estimates': {
                'total_estimated': total_estimated,
                'total_actual': total_actual,
                'remaining_estimated': total_estimated - total_actual
            }
        }
    
    def _analyze_dependencies(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Analyze task dependencies"""
        if not self.active_plan or self.active_plan not in self.plans:
            return {'error': 'No active plan'}
        
        plan = self.plans[self.active_plan]
        
        # Build dependency graph
        dependency_graph = {}
        for task in plan.tasks:
            dependency_graph[task.id] = {
                'title': task.title,
                'status': task.status.value,
                'dependencies': task.dependencies,
                'blocked_by': [],
                'blocking': []
            }
        
        # Find blocking relationships
        for task_id, task_info in dependency_graph.items():
            for dep_id in task_info['dependencies']:
                if dep_id in dependency_graph:
                    dependency_graph[dep_id]['blocking'].append(task_id)
                    dependency_graph[task_id]['blocked_by'].append(dep_id)
        
        return {
            'plan_id': plan.id,
            'dependency_analysis': dependency_graph,
            'total_dependencies': sum(len(info['dependencies']) for info in dependency_graph.values())
        }
    
    def _estimate_time(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Estimate time for plan completion"""
        if not self.active_plan or self.active_plan not in self.plans:
            return {'error': 'No active plan'}
        
        plan = self.plans[self.active_plan]
        
        # Calculate estimates
        remaining_tasks = [t for t in plan.tasks if t.status != TaskStatus.COMPLETED]
        total_estimated = sum(t.estimated_time for t in remaining_tasks)
        
        # Priority breakdown
        priority_breakdown = {
            'CRITICAL': sum(t.estimated_time for t in remaining_tasks if t.priority == TaskPriority.CRITICAL),
            'HIGH': sum(t.estimated_time for t in remaining_tasks if t.priority == TaskPriority.HIGH),
            'MEDIUM': sum(t.estimated_time for t in remaining_tasks if t.priority == TaskPriority.MEDIUM),
            'LOW': sum(t.estimated_time for t in remaining_tasks if t.priority == TaskPriority.LOW)
        }
        
        return {
            'plan_id': plan.id,
            'total_estimated_minutes': total_estimated,
            'total_estimated_hours': round(total_estimated / 60, 1),
            'remaining_tasks': len(remaining_tasks),
            'priority_breakdown_minutes': priority_breakdown
        }
    
    def _update_priority(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Update task priority"""
        return {'message': 'Priority update functionality integrated with update_task'}
    
    def _track_progress(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Track progress across all plans"""
        if not self.plans:
            return {'message': 'No plans to track'}
        
        total_plans = len(self.plans)
        completed_plans = 0
        total_tasks = 0
        completed_tasks = 0
        
        for plan in self.plans.values():
            plan_tasks = len(plan.tasks)
            plan_completed = len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED])
            
            total_tasks += plan_tasks
            completed_tasks += plan_completed
            
            if plan_tasks > 0 and plan_completed == plan_tasks:
                completed_plans += 1
        
        return {
            'total_plans': total_plans,
            'completed_plans': completed_plans,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'overall_progress': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
        }
    
    def _export_plan(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Export plan to file"""
        if not self.active_plan or self.active_plan not in self.plans:
            return {'error': 'No active plan to export'}
        
        plan = self.plans[self.active_plan]
        
        # Convert to exportable format
        export_data = {
            'plan': asdict(plan),
            'exported_at': time.time(),
            'version': self.version
        }
        
        # Convert enums to strings for JSON serialization
        for task_data in export_data['plan']['tasks']:
            task_data['priority'] = task_data['priority'].name if hasattr(task_data['priority'], 'name') else str(task_data['priority'])
            task_data['status'] = task_data['status'].value if hasattr(task_data['status'], 'value') else str(task_data['status'])
        
        return {
            'export_data': export_data,
            'plan_id': plan.id,
            'plan_name': plan.name,
            'tasks_count': len(plan.tasks)
        }
    
    def _import_plan(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Import plan from data"""
        return {'message': 'Plan import functionality requires file handling'}
    
    def _save_plans(self):
        """Save plans to file (placeholder)"""
        # Future: implement persistent storage
        pass
    
    def _load_saved_plans(self):
        """Load saved plans (placeholder)"""
        # Future: implement persistent storage loading
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get planning tool status"""
        return {
            'tool_name': self.name,
            'version': self.version,
            'total_plans': len(self.plans),
            'active_plan': self.active_plan,
            'total_tasks': sum(len(plan.tasks) for plan in self.plans.values()),
            'capabilities': self.capabilities
        }