<?php
namespace App\Command;

use Doctrine\DBAL\Connection;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputArgument;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;

#[AsCommand(name: 'app:user:disable')]
final class DisableUserCommand extends Command
{
    public function __construct(private Connection $db) { parent::__construct(); }
    protected function configure(): void { $this->addArgument('email', InputArgument::REQUIRED); }
    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $id = $this->db->fetchOne('SELECT id FROM users WHERE email = ?', [strtolower($input->getArgument('email'))]);
        if (!$id) { $output->writeln('<error>User not found</error>'); return Command::FAILURE; }
        $this->db->update('users', ['disabled' => 1], ['id' => $id]);
        $this->db->executeStatement('UPDATE refresh_tokens SET revoked_at = UTC_TIMESTAMP() WHERE user_id = ?', [$id]);
        $output->writeln('User disabled'); return Command::SUCCESS;
    }
}
