from django.core.management.base import BaseCommand
import time
import os

from Appraise.settings import MIDDLEWARE_LOG_FILENAME


class Command(BaseCommand):
    help = 'Tail the middleware log file (MIDDLEWARE_LOG_FILENAME)\n\nExamples:\n  python manage.py tail_middleware_log --follow\n  python manage.py tail_middleware_log --filter crowdee_user_id\n'

    def add_arguments(self, parser):
        parser.add_argument('--follow', '-f', action='store_true', help='Follow the log file')
        parser.add_argument('--filter', '-g', dest='filter', type=str, help='Only show lines that contain this substring')

    def handle(self, *args, **options):
        path = MIDDLEWARE_LOG_FILENAME
        follow = options.get('follow', False)
        substr = options.get('filter')

        if not os.path.exists(path):
            self.stderr.write('Middleware log file not found: {}'.format(path))
            return

        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                # If following, seek to the end
                if follow:
                    fh.seek(0, os.SEEK_END)

                # Print existing contents (or tail next lines if follow)
                for line in fh:
                    if substr and substr not in line:
                        continue
                    self.stdout.write(line.rstrip())

                if follow:
                    while True:
                        where = fh.tell()
                        line = fh.readline()
                        if not line:
                            time.sleep(0.5)
                            fh.seek(where)
                        else:
                            if substr and substr not in line:
                                continue
                            self.stdout.write(line.rstrip())
                            self.stdout.flush()
        except KeyboardInterrupt:
            # Allow Ctrl-C to exit cleanly
            self.stdout.write('\nStopped following log.')
        except Exception as exc:
            self.stderr.write('Error while reading middleware log: {}'.format(exc))

