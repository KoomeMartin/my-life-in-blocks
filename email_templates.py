"""
HTML Email Templates for REVIEWER Agent Reports
Beautiful, responsive email templates for weekly reviews and progress reports
"""
from typing import Dict, Any, List
from datetime import datetime

def weekly_review_template(
    date_range: str,
    productivity_metrics: Dict[str, Any],
    energy_alignment: Dict[str, Any],
    insights: List[str],
    recommendations: List[str],
    achievements: List[str],
    improvements: List[str],
    week_over_week: Dict[str, str] = None
) -> str:
    """
    Generate HTML template for weekly review email
    
    Args:
        date_range: Date range string (e.g., "Feb 11-18, 2026")
        productivity_metrics: Dict with tasks_completed, time_utilization, events_attended, etc.
        energy_alignment: Dict with peak_hour_usage, low_energy_usage, alignment_score
        insights: List of key insights
        recommendations: List of recommendations
        achievements: List of achievements
        improvements: List of areas for improvement
        week_over_week: Optional dict with trend data
    
    Returns:
        str: HTML email content
    """
    
    # Build metrics HTML
    metrics_html = ""
    for key, value in productivity_metrics.items():
        icon = "✅" if "completed" in key.lower() else "⏰" if "time" in key.lower() else "📅"
        label = key.replace("_", " ").title()
        metrics_html += f'<p><strong>{icon} {label}:</strong> {value}</p>\n'
    
    # Build energy alignment HTML
    energy_html = ""
    for key, value in energy_alignment.items():
        icon = "✅" if "peak" in key.lower() else "⚠️" if "low" in key.lower() else "📈"
        label = key.replace("_", " ").title()
        energy_html += f'<p><strong>{icon} {label}:</strong> {value}</p>\n'
    
    # Build insights HTML
    insights_html = "\n".join([f'<li>{insight}</li>' for insight in insights])
    
    # Build recommendations HTML
    recommendations_html = "\n".join([f'<li>{rec}</li>' for rec in recommendations])
    
    # Build achievements HTML
    achievements_html = "\n".join([f'<li>{achievement}</li>' for achievement in achievements])
    
    # Build improvements HTML
    improvements_html = "\n".join([f'<li>{improvement}</li>' for improvement in improvements])
    
    # Build week-over-week trends HTML
    trends_html = ""
    if week_over_week:
        trends_html = "<h2 style='color: #667eea; margin-top: 30px;'>📈 Week-over-Week Trends</h2>"
        trends_html += "<div style='background: white; padding: 15px; border-radius: 8px; margin: 10px 0;'>"
        for metric, change in week_over_week.items():
            trends_html += f"<p><strong>{metric}:</strong> {change}</p>"
        trends_html += "</div>"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Weekly Review</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 40px 30px; text-align: center; color: white;">
                <h1 style="margin: 0; font-size: 32px;">📊 Weekly Review</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.9;">{date_range}</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px;">
                <!-- Productivity Metrics -->
                <h2 style="color: #667eea; margin-top: 0;">🎯 Productivity Metrics</h2>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
                    {metrics_html}
                </div>
                
                <!-- Energy Alignment -->
                <h2 style="color: #667eea; margin-top: 30px;">⚡ Energy Alignment</h2>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
                    {energy_html}
                </div>
                
                <!-- Key Insights -->
                <h2 style="color: #667eea; margin-top: 30px;">🔍 Key Insights</h2>
                <ul style="background: #f8f9fa; padding: 20px 20px 20px 40px; 
                           border-radius: 8px; margin: 15px 0; line-height: 1.8;">
                    {insights_html}
                </ul>
                
                {trends_html}
                
                <!-- Recommendations -->
                <h2 style="color: #667eea; margin-top: 30px;">🎯 Recommendations</h2>
                <ol style="background: #e8f5e9; padding: 20px 20px 20px 40px; 
                           border-radius: 8px; margin: 15px 0; line-height: 1.8;">
                    {recommendations_html}
                </ol>
                
                <!-- Achievements -->
                <h2 style="color: #667eea; margin-top: 30px;">💪 Achievements</h2>
                <ul style="background: #fff3e0; padding: 20px 20px 20px 40px; 
                           border-radius: 8px; margin: 15px 0; line-height: 1.8;">
                    {achievements_html}
                </ul>
                
                <!-- Areas for Improvement -->
                <h2 style="color: #667eea; margin-top: 30px;">⚠️ Areas for Improvement</h2>
                <ul style="background: #ffebee; padding: 20px 20px 20px 40px; 
                           border-radius: 8px; margin: 15px 0; line-height: 1.8;">
                    {improvements_html}
                </ul>
                
                <!-- Motivational Message -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 25px; border-radius: 8px; margin: 30px 0; text-align: center; color: white;">
                    <p style="margin: 0; font-size: 18px; font-weight: bold;">Keep up the great work! 💪</p>
                    <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.9;">
                        You're making excellent progress toward your goals.
                    </p>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #333; color: white; padding: 25px; text-align: center;">
                <p style="margin: 0; font-size: 14px;">Generated by My Life in Blocks</p>
                <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.7;">
                    Your AI-powered productivity assistant
                </p>
                <p style="margin: 15px 0 0 0; font-size: 11px; opacity: 0.6;">
                    {datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")}
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def progress_report_template(
    title: str,
    summary: str,
    metrics: Dict[str, Any],
    next_steps: List[str]
) -> str:
    """
    Generate HTML template for progress report email
    
    Args:
        title: Report title
        summary: Summary text
        metrics: Dict of metrics to display
        next_steps: List of next steps
    
    Returns:
        str: HTML email content
    """
    
    # Build metrics HTML
    metrics_html = ""
    for key, value in metrics.items():
        label = key.replace("_", " ").title()
        metrics_html += f'<p><strong>{label}:</strong> {value}</p>\n'
    
    # Build next steps HTML
    next_steps_html = "\n".join([f'<li>{step}</li>' for step in next_steps])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 40px 30px; text-align: center; color: white;">
                <h1 style="margin: 0; font-size: 28px;">📈 {title}</h1>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px;">
                <!-- Summary -->
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
                    <p style="margin: 0; line-height: 1.6;">{summary}</p>
                </div>
                
                <!-- Metrics -->
                <h2 style="color: #667eea; margin-top: 30px;">📊 Metrics</h2>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
                    {metrics_html}
                </div>
                
                <!-- Next Steps -->
                <h2 style="color: #667eea; margin-top: 30px;">🎯 Next Steps</h2>
                <ol style="background: #e8f5e9; padding: 20px 20px 20px 40px; 
                           border-radius: 8px; margin: 15px 0; line-height: 1.8;">
                    {next_steps_html}
                </ol>
            </div>
            
            <!-- Footer -->
            <div style="background: #333; color: white; padding: 25px; text-align: center;">
                <p style="margin: 0; font-size: 14px;">Generated by My Life in Blocks</p>
                <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.7;">
                    Your AI-powered productivity assistant
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def simple_notification_template(
    title: str,
    message: str,
    emoji: str = "📧"
) -> str:
    """
    Generate simple notification email template
    
    Args:
        title: Notification title
        message: Notification message
        emoji: Emoji to display
    
    Returns:
        str: HTML email content
    """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 40px 30px; text-align: center; color: white;">
                <h1 style="margin: 0; font-size: 48px;">{emoji}</h1>
                <h2 style="margin: 15px 0 0 0; font-size: 24px;">{title}</h2>
            </div>
            
            <!-- Content -->
            <div style="padding: 40px 30px;">
                <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #333;">
                    {message}
                </p>
            </div>
            
            <!-- Footer -->
            <div style="background: #333; color: white; padding: 25px; text-align: center;">
                <p style="margin: 0; font-size: 14px;">Generated by My Life in Blocks</p>
                <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.7;">
                    Your AI-powered productivity assistant
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html
