<?php
namespace App\Command;

use App\Service\PasswordHasher;
use Doctrine\DBAL\Connection;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputArgument;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;

#[AsCommand(name: 'app:user:reset-password')]
final class ResetPasswordCommand extends Command
{
    public function __construct(private Connection $db, private PasswordHasher $hasher = new PasswordHasher()) { parent::__construct(); }
    protected function configure(): void { $this->addArgument('email', InputArgument::REQUIRED); }
    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $password = getenv('APP_USER_PASSWORD') ?: '';
        if ($error = PasswordHasher::policyError($password)) { $output->writeln("<error>APP_USER_PASSWORD: $error</error>"); return Command::FAILURE; }
        $id = $this->db->fetchOne('SELECT id FROM users WHERE email = ?', [strtolower($input->getArgument('email'))]);
        if (!$id) { $output->writeln('<error>User not found</error>'); return Command::FAILURE; }
        $this->db->update('users', ['password_hash' => $this->hasher->hash($password)], ['id' => $id]);
        $this->db->executeStatement('UPDATE refresh_tokens SET revoked_at = UTC_TIMESTAMP() WHERE user_id = ?', [$id]);
        $output->writeln('Password reset'); return Command::SUCCESS;
    }
}
