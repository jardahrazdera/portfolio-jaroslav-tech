"""
Management command to set up and manage automatic cleanup system.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
import subprocess
import sys
import os


class Command(BaseCommand):
    help = 'Set up and manage the automatic image cleanup system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--install',
            action='store_true',
            help='Install cron jobs for automatic cleanup',
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Remove all cleanup cron jobs',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show status of cleanup system',
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test all cleanup functions',
        )
        parser.add_argument(
            '--logs',
            action='store_true',
            help='Show recent cleanup logs',
        )

    def handle(self, *args, **options):
        if options['install']:
            self.install_cron_jobs()
        elif options['remove']:
            self.remove_cron_jobs()
        elif options['status']:
            self.show_status()
        elif options['test']:
            self.test_cleanup_system()
        elif options['logs']:
            self.show_logs()
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Please specify an action: --install, --remove, --status, --test, or --logs'
                )
            )

    def install_cron_jobs(self):
        """Install the cron jobs for automatic cleanup."""
        try:
            self.stdout.write(self.style.SUCCESS('🚀 Installing automatic cleanup cron jobs...'))

            # Use django-crontab to install cron jobs
            call_command('crontab', 'add')

            self.stdout.write(self.style.SUCCESS('✅ Cron jobs installed successfully!'))
            self.stdout.write('\n📅 Scheduled cleanup jobs:')
            self.stdout.write('  • Daily cleanup: Every day at 3:00 AM')
            self.stdout.write('  • Weekly analysis: Every Sunday at 2:00 AM')
            self.stdout.write('  • Monthly report: 1st day of month at 1:00 AM')
            self.stdout.write('\n📝 Logs will be written to: /tmp/django_cron.log')
            self.stdout.write('💡 Use --status to check if jobs are running')

        except Exception as e:
            raise CommandError(f'Failed to install cron jobs: {str(e)}')

    def remove_cron_jobs(self):
        """Remove all cleanup cron jobs."""
        try:
            self.stdout.write(self.style.WARNING('🗑️  Removing cleanup cron jobs...'))

            # Use django-crontab to remove cron jobs
            call_command('crontab', 'remove')

            self.stdout.write(self.style.SUCCESS('✅ Cron jobs removed successfully!'))
            self.stdout.write('⚠️  Automatic cleanup is now disabled.')
            self.stdout.write('💡 Middleware-based cleanup will still work on active requests.')

        except Exception as e:
            raise CommandError(f'Failed to remove cron jobs: {str(e)}')

    def show_status(self):
        """Show the current status of the cleanup system."""
        self.stdout.write(self.style.SUCCESS('📊 Cleanup System Status'))
        self.stdout.write('=' * 60)

        # Check cron jobs
        try:
            # List current cron jobs
            call_command('crontab', 'show')
            cron_status = '✅ Active'
        except:
            cron_status = '❌ Not installed'

        self.stdout.write(f'Cron Jobs: {cron_status}')

        # Check middleware configuration
        middleware_installed = any(
            'blog.middleware' in mw for mw in settings.MIDDLEWARE
        )
        middleware_status = '✅ Active' if middleware_installed else '❌ Not configured'
        self.stdout.write(f'Middleware: {middleware_status}')

        # Check logging configuration
        logging_configured = hasattr(settings, 'LOGGING') and 'blog.cron' in settings.LOGGING.get('loggers', {})
        logging_status = '✅ Configured' if logging_configured else '❌ Not configured'
        self.stdout.write(f'Logging: {logging_status}')

        # Check cleanup statistics
        try:
            from blog.middleware import get_cleanup_stats
            stats = get_cleanup_stats()

            if stats:
                from datetime import datetime
                last_cleanup = datetime.fromtimestamp(stats.get('last_cleanup', 0))
                self.stdout.write(f'Last Cleanup: {last_cleanup.strftime("%Y-%m-%d %H:%M:%S")}')
                self.stdout.write(f'Files Cleaned: {stats.get("last_files_cleaned", 0)}')
                self.stdout.write(f'Storage Usage: {stats.get("total_storage_mb", 0):.1f} MB')
            else:
                self.stdout.write('Last Cleanup: Never')

        except Exception as e:
            self.stdout.write(f'Cleanup Stats: Error - {str(e)}')

        # Show configuration
        self.stdout.write('\n⚙️  Configuration:')
        cleanup_interval = getattr(settings, 'BLOG_CLEANUP_INTERVAL', 1000)
        monitoring_interval = getattr(settings, 'BLOG_MONITORING_INTERVAL', 5000)
        self.stdout.write(f'  • Cleanup interval: Every {cleanup_interval} requests')
        self.stdout.write(f'  • Monitoring interval: Every {monitoring_interval} requests')

    def test_cleanup_system(self):
        """Test all components of the cleanup system."""
        self.stdout.write(self.style.SUCCESS('🧪 Testing Cleanup System'))
        self.stdout.write('=' * 60)

        # Test basic cleanup functionality
        try:
            from blog.signals import cleanup_orphaned_files, get_storage_stats

            self.stdout.write('1️⃣  Testing orphaned file cleanup...')
            cleaned_count = cleanup_orphaned_files()
            self.stdout.write(f'   ✅ Found and cleaned {cleaned_count} orphaned files')

            self.stdout.write('2️⃣  Testing storage statistics...')
            stats = get_storage_stats()
            total_mb = stats['total_size'] / (1024 * 1024)
            self.stdout.write(f'   ✅ Current storage: {total_mb:.1f} MB')
            self.stdout.write(f'   📸 Featured images: {stats["featured_images"]["count"]} files')
            self.stdout.write(f'   🔄 Processed images: {stats["processed_images"]["count"]} files')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Cleanup test failed: {str(e)}'))

        # Test cron job functions
        try:
            from blog.cron import test_cron_jobs

            self.stdout.write('3️⃣  Testing cron job functions...')
            result1, result2, result3 = test_cron_jobs()
            self.stdout.write('   ✅ All cron jobs tested successfully')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Cron test failed: {str(e)}'))

        # Test middleware functions
        try:
            from blog.middleware import get_cleanup_stats, reset_cleanup_counters

            self.stdout.write('4️⃣  Testing middleware functions...')
            stats = get_cleanup_stats()
            self.stdout.write('   ✅ Middleware stats accessible')

            # Reset counters as part of test
            reset_cleanup_counters()
            self.stdout.write('   ✅ Cleanup counters reset')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Middleware test failed: {str(e)}'))

        self.stdout.write('\n🎉 Cleanup system testing completed!')

    def show_logs(self):
        """Show recent cleanup logs."""
        self.stdout.write(self.style.SUCCESS('📋 Recent Cleanup Logs'))
        self.stdout.write('=' * 60)

        log_files = [
            '/tmp/django_cron.log',
            '/tmp/django_cleanup.log',
        ]

        for log_file in log_files:
            if os.path.exists(log_file):
                self.stdout.write(f'\n📄 {log_file}:')
                try:
                    # Show last 20 lines
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        recent_lines = lines[-20:] if len(lines) > 20 else lines

                        if recent_lines:
                            for line in recent_lines:
                                self.stdout.write(f'  {line.strip()}')
                        else:
                            self.stdout.write('  (empty)')

                except Exception as e:
                    self.stdout.write(f'  Error reading log: {str(e)}')
            else:
                self.stdout.write(f'\n📄 {log_file}: (not found)')

        self.stdout.write('\n💡 Tip: Use "tail -f /tmp/django_cleanup.log" to follow logs in real-time')

    def print_help_text(self):
        """Print helpful information about the cleanup system."""
        self.stdout.write(self.style.SUCCESS('\n📖 Cleanup System Help'))
        self.stdout.write('=' * 60)

        self.stdout.write('🎯 Purpose:')
        self.stdout.write('  Automatically clean up orphaned image files to prevent storage bloat.')

        self.stdout.write('\n🔧 Components:')
        self.stdout.write('  • Django signals: Clean up on post delete/image change')
        self.stdout.write('  • Cron jobs: Scheduled daily/weekly/monthly cleanup')
        self.stdout.write('  • Middleware: Request-based periodic cleanup')
        self.stdout.write('  • Admin actions: Manual cleanup triggers')

        self.stdout.write('\n📅 Schedule:')
        self.stdout.write('  • Daily: 3:00 AM - Orphaned file cleanup')
        self.stdout.write('  • Weekly: Sunday 2:00 AM - Storage analysis')
        self.stdout.write('  • Monthly: 1st day 1:00 AM - Comprehensive report')

        self.stdout.write('\n🚀 Quick Start:')
        self.stdout.write('  1. python manage.py setup_cleanup --install')
        self.stdout.write('  2. python manage.py setup_cleanup --status')
        self.stdout.write('  3. python manage.py setup_cleanup --test')

        self.stdout.write('\n📊 Monitoring:')
        self.stdout.write('  • Check Django admin for cleanup status')
        self.stdout.write('  • Monitor logs: tail -f /tmp/django_cleanup.log')
        self.stdout.write('  • Use --status for quick health check')