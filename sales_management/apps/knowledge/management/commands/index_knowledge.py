from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.services import KnowledgeDependencyError, KnowledgeService


class Command(BaseCommand):
    help = "Index curated project documents into the local Chroma RAG store."

    def add_arguments(self, parser):
        parser.add_argument("--rebuild", action="store_true", help="Xóa collection trước khi index")
        parser.add_argument("--include-code", action="store_true", help="Index thêm Python code của hai skeleton")
        parser.add_argument("--max-chars", type=int, default=1800)

    def handle(self, *args, **options):
        try:
            result = KnowledgeService().index(
                rebuild=options["rebuild"],
                include_code=options["include_code"],
                max_chars=options["max_chars"],
            )
        except (KnowledgeDependencyError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                "Indexed {files} files / {chunks} chunks; collection={collection_count}; store={store_path}".format(
                    **result
                )
            )
        )
