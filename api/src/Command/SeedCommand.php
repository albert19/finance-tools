<?php
namespace App\Command;

use App\Service\PasswordHasher;
use Doctrine\DBAL\Connection;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Uid\Uuid;

#[AsCommand(name: 'app:seed', description: 'Idempotently create the configured first administrator')]
final class SeedCommand extends Command
{
    public function __construct(private Connection $db, private PasswordHasher $hasher = new PasswordHasher()) { parent::__construct(); }
    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $email = strtolower(trim(getenv('SEED_ADMIN_EMAIL') ?: ''));
        $passwordFile = getenv('SEED_ADMIN_PASSWORD_FILE');
        $password = $passwordFile ? @file_get_contents($passwordFile) : false;
        $password = $password === false ? '' : rtrim($password, "\r\n");
        if (!$email) { $output->writeln('SEED_ADMIN_EMAIL absent; nothing to seed'); return Command::SUCCESS; }
        if (!filter_var($email, FILTER_VALIDATE_EMAIL) || PasswordHasher::policyError($password)) { $output->writeln('<error>Valid email and a password of 12 to 1024 characters without spaces required</error>'); return Command::FAILURE; }
        if (!$this->db->fetchOne('SELECT id FROM users WHERE email = ?', [$email])) {
            $this->db->insert('users', ['id' => Uuid::v7()->toRfc4122(), 'email' => $email,
                'password_hash' => $this->hasher->hash($password), 'roles' => json_encode(['ROLE_USER', 'ROLE_ADMIN']), 'locale' => 'en', 'disabled' => 0]);
            $output->writeln('Administrator created');
        } else { $output->writeln('Administrator already exists'); }
        return Command::SUCCESS;
    }
}
