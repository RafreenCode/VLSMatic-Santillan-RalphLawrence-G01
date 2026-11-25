from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from network_projects.models import NetworkProject, SubnetRequirement


class CoreAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner", "owner@example.com", "SafePassword!327")
        cls.other = User.objects.create_user("other", "other@example.com", "SafePassword!327")
        cls.admin = User.objects.create_user("admin", "admin@example.com", "SafePassword!327", role=User.Role.ADMIN)
        cls.project = NetworkProject.objects.create(owner=cls.owner, name="Private", base_network="10.0.0.0", prefix_length=24)
        cls.subnet = SubnetRequirement.objects.create(project=cls.project, name="Lab", required_hosts=20)

    def mutation_urls(self):
        return [reverse("network_projects:" + name, args=args) for name, args in (
            ("update", [self.project.slug]), ("delete", [self.project.slug]),
            ("calculate", [self.project.slug]), ("requirement_create", [self.project.slug]),
            ("requirement_update", [self.project.slug, self.subnet.pk]),
            ("requirement_delete", [self.project.slug, self.subnet.pk]),
        )]

    def test_every_core_endpoint_requires_login(self):
        urls = self.mutation_urls() + [reverse("network_projects:" + name, args=args) for name, args in (
            ("list", []), ("create", []), ("detail", [self.project.slug]),
        )]
        for url in urls:
            for method in (self.client.get, self.client.post):
                with self.subTest(url=url, method=method.__name__):
                    response = method(url)
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response.url.startswith(reverse("accounts:login") + "?next="))

    def test_mutations_reject_get_and_head_without_changes(self):
        self.client.force_login(self.owner)
        for url in self.mutation_urls():
            for method in (self.client.get, self.client.head):
                with self.subTest(url=url, method=method.__name__):
                    self.assertEqual(method(url).status_code, 405)
        self.assertTrue(NetworkProject.objects.filter(pk=self.project.pk).exists())
        self.subnet.refresh_from_db()
        self.assertEqual(self.subnet.required_hosts, 20)

    def test_other_user_cannot_post_to_any_owned_endpoint(self):
        self.client.force_login(self.other)
        for url in self.mutation_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, {"name": "Stolen", "required_hosts": 2}).status_code, 404)
        self.subnet.refresh_from_db()
        self.assertEqual(self.subnet.name, "Lab")

    def test_admin_cannot_mutate_another_users_project(self):
        self.client.force_login(self.admin)
        for url in self.mutation_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 403)

    def test_nested_subnet_must_belong_to_url_project(self):
        second = NetworkProject.objects.create(owner=self.owner, name="Second", base_network="10.1.0.0", prefix_length=24)
        self.client.force_login(self.owner)
        for name in ("requirement_update", "requirement_delete"):
            url = reverse("network_projects:" + name, args=[second.slug, self.subnet.pk])
            self.assertEqual(self.client.post(url, {"name": "Wrong", "required_hosts": 10}).status_code, 404)

    def test_real_csrf_checks_reject_missing_tokens(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for url in self.mutation_urls() + [reverse("network_projects:create")]:
            with self.subTest(url=url):
                self.assertEqual(client.post(url).status_code, 403)

    def test_real_csrf_token_allows_valid_create(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        url = reverse("network_projects:create")
        client.get(url)
        response = client.post(url, {
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            "name": "CSRF verified", "base_network": "10.2.0.0", "prefix_length": 24,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NetworkProject.objects.filter(name="CSRF verified", owner=self.owner).exists())
