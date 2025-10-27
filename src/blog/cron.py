"""
Automated cron jobs for blog image cleanup and storage management.
These functions are called by django-crontab on scheduled intervals.
"""
import logging
from datetime import datetime, timedelta
from django.core.mail import mail_admins
from django.conf import settings
from .signals import cleanup_orphaned_files, get_storage_stats, format_file_size
from .models import Post

logger = logging.getLogger(__name__)


def daily_cleanup_orphaned_files():
    """
    Daily cron job to clean up orphaned files.
    Runs at 3:00 AM every day to remove unused images and files.
    """
    try:
        logger.info("Starting daily orphaned file cleanup...")
        start_time = datetime.now()

        # Run the cleanup
        cleaned_count = cleanup_orphaned_files()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"Daily cleanup completed: {cleaned_count} files removed in {duration:.2f} seconds")

        # Log to cron log for external monitoring
        print(f"[{datetime.now()}] Daily cleanup: {cleaned_count} files removed")

        return f"Success: {cleaned_count} files cleaned"

    except Exception as e:
        error_msg = f"Daily cleanup failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"[{datetime.now()}] ERROR: {error_msg}")

        # Send error notification to admins if configured
        try:
            mail_admins(
                subject="Blog Cleanup Error",
                message=f"Daily orphaned file cleanup failed: {str(e)}",
                fail_silently=True
            )
        except:
            pass  # Don't fail if email isn't configured

        return f"Error: {error_msg}"


def weekly_storage_analysis():
    """
    Weekly cron job for deep storage analysis.
    Runs every Sunday at 2:00 AM to analyze storage patterns and health.
    """
    try:
        logger.info("Starting weekly storage analysis...")
        start_time = datetime.now()

        # Get current storage stats
        stats = get_storage_stats()

        # Analyze storage health
        analysis = {
            'total_size_mb': stats['total_size'] / (1024 * 1024),
            'featured_images': stats['featured_images'],
            'processed_images': stats['processed_images'],
            'blog_files': stats['blog_files'],
            'optimization_ratio': stats['processed_images']['count'] / max(stats['featured_images']['count'], 1),
        }

        # Get posts without images for analysis
        posts_without_images = Post.objects.filter(featured_image='').count()
        total_posts = Post.objects.count()
        image_coverage = ((total_posts - posts_without_images) / max(total_posts, 1)) * 100

        # Run cleanup to check for orphaned files
        cleanup_count = cleanup_orphaned_files()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Create detailed report
        report = f"""
Weekly Storage Analysis Report - {start_time.strftime('%Y-%m-%d %H:%M:%S')}
==========================================================================

Storage Overview:
- Total Storage Used: {format_file_size(stats['total_size'])}
- Featured Images: {stats['featured_images']['count']} files ({format_file_size(stats['featured_images']['size'])})
- Processed Images: {stats['processed_images']['count']} files ({format_file_size(stats['processed_images']['size'])})
- Blog Files: {stats['blog_files']['count']} files ({format_file_size(stats['blog_files']['size'])})

Content Analysis:
- Total Posts: {total_posts}
- Posts with Images: {total_posts - posts_without_images}
- Image Coverage: {image_coverage:.1f}%
- Optimization Ratio: {analysis['optimization_ratio']:.1f}x

Cleanup Results:
- Orphaned Files Found: {cleanup_count}
- Analysis Duration: {duration:.2f} seconds

Health Status: {'✓ HEALTHY' if cleanup_count == 0 and analysis['total_size_mb'] < 1000 else '⚠ ATTENTION NEEDED'}
        """

        logger.info(f"Weekly analysis completed: {cleanup_count} orphaned files found")
        logger.info(f"Storage health: {format_file_size(stats['total_size'])} total usage")

        # Log to cron log
        print(f"[{datetime.now()}] Weekly analysis: {cleanup_count} orphaned files, {format_file_size(stats['total_size'])} total")

        # Send detailed report to admins if there are issues
        if cleanup_count > 0 or analysis['total_size_mb'] > 1000:
            try:
                mail_admins(
                    subject="Blog Storage Weekly Report - Attention Needed",
                    message=report,
                    fail_silently=True
                )
            except:
                pass

        return f"Success: Analysis complete, {cleanup_count} orphaned files found"

    except Exception as e:
        error_msg = f"Weekly storage analysis failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"[{datetime.now()}] ERROR: {error_msg}")

        try:
            mail_admins(
                subject="Blog Storage Analysis Error",
                message=f"Weekly storage analysis failed: {str(e)}",
                fail_silently=True
            )
        except:
            pass

        return f"Error: {error_msg}"


def monthly_storage_report():
    """
    Monthly cron job for comprehensive storage reporting.
    Runs on the 1st day of each month at 1:00 AM.
    """
    try:
        logger.info("Starting monthly storage report...")
        start_time = datetime.now()

        # Get current storage stats
        stats = get_storage_stats()

        # Get content statistics
        total_posts = Post.objects.count()
        published_posts = Post.objects.filter(is_published=True).count()
        posts_with_images = Post.objects.exclude(featured_image='').count()
        recent_posts = Post.objects.filter(
            created_at__gte=datetime.now() - timedelta(days=30)
        ).count()

        # Run cleanup for monthly maintenance
        cleanup_count = cleanup_orphaned_files()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Create comprehensive monthly report
        report = f"""
Monthly Blog Storage Report - {start_time.strftime('%B %Y')}
==========================================================================

STORAGE SUMMARY:
- Total Storage Used: {format_file_size(stats['total_size'])}
- Featured Images: {stats['featured_images']['count']} files ({format_file_size(stats['featured_images']['size'])})
- Processed Images: {stats['processed_images']['count']} files ({format_file_size(stats['processed_images']['size'])})
- Blog Attachments: {stats['blog_files']['count']} files ({format_file_size(stats['blog_files']['size'])})

CONTENT STATISTICS:
- Total Posts: {total_posts}
- Published Posts: {published_posts}
- Posts with Featured Images: {posts_with_images}
- New Posts This Month: {recent_posts}
- Image Coverage: {(posts_with_images / max(total_posts, 1) * 100):.1f}%

MAINTENANCE SUMMARY:
- Orphaned Files Cleaned: {cleanup_count}
- Report Generation Time: {duration:.2f} seconds
- Last Cleanup: {start_time.strftime('%Y-%m-%d %H:%M:%S')}

RECOMMENDATIONS:
{_generate_storage_recommendations(stats, total_posts, posts_with_images)}

==========================================================================
Generated by Django Blog Automated Cleanup System
        """

        logger.info(f"Monthly report completed: {cleanup_count} orphaned files cleaned")
        print(f"[{datetime.now()}] Monthly report: {cleanup_count} files cleaned, {format_file_size(stats['total_size'])} total storage")

        # Always send monthly report to admins
        try:
            mail_admins(
                subject=f"Blog Storage Monthly Report - {start_time.strftime('%B %Y')}",
                message=report,
                fail_silently=True
            )
        except:
            pass

        return f"Success: Monthly report generated, {cleanup_count} files cleaned"

    except Exception as e:
        error_msg = f"Monthly storage report failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"[{datetime.now()}] ERROR: {error_msg}")

        try:
            mail_admins(
                subject="Blog Storage Monthly Report Error",
                message=f"Monthly storage report generation failed: {str(e)}",
                fail_silently=True
            )
        except:
            pass

        return f"Error: {error_msg}"


def _generate_storage_recommendations(stats, total_posts, posts_with_images):
    """Generate storage optimization recommendations based on current stats."""
    recommendations = []

    total_size_mb = stats['total_size'] / (1024 * 1024)
    optimization_ratio = stats['processed_images']['count'] / max(stats['featured_images']['count'], 1)
    image_coverage = (posts_with_images / max(total_posts, 1)) * 100

    # Storage size recommendations
    if total_size_mb > 1000:
        recommendations.append("⚠ Storage usage over 1GB - consider archiving old content or optimizing images")
    elif total_size_mb > 500:
        recommendations.append("➤ Storage usage over 500MB - monitor growth trends")
    else:
        recommendations.append("✓ Storage usage is healthy")

    # Optimization ratio recommendations
    if optimization_ratio > 20:
        recommendations.append("⚠ High processed-to-original ratio - check for duplicate processing")
    elif optimization_ratio < 5:
        recommendations.append("➤ Low optimization ratio - more responsive sizes could be beneficial")
    else:
        recommendations.append("✓ Image optimization ratio is good")

    # Content recommendations
    if image_coverage < 50:
        recommendations.append(f"➤ Only {image_coverage:.1f}% of posts have featured images - consider adding more visual content")
    else:
        recommendations.append(f"✓ Good image coverage ({image_coverage:.1f}% of posts have featured images)")

    if not recommendations:
        recommendations.append("✓ All storage metrics look healthy")

    return "\n".join(f"- {rec}" for rec in recommendations)


# Utility function for manual testing
def test_cron_jobs():
    """
    Test function to manually run all cron jobs.
    Not called by crontab - for development/testing only.
    """
    print("Testing all cron jobs...")

    print("\n1. Testing daily cleanup...")
    result1 = daily_cleanup_orphaned_files()
    print(f"Result: {result1}")

    print("\n2. Testing weekly analysis...")
    result2 = weekly_storage_analysis()
    print(f"Result: {result2}")

    print("\n3. Testing monthly report...")
    result3 = monthly_storage_report()
    print(f"Result: {result3}")

    print("\nAll cron job tests completed!")
    return result1, result2, result3