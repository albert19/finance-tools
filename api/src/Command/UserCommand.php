<?php
namespace App\Command;

use App\Service\PasswordHasher;
use Doctrine\DBAL\Connection;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputArgument;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Question\Question;
use Symfony\Component\Uid\Uuid;

#[AsCommand(name: 'app:user:create')]
final class UserCommand extends Command
{
    public function __construct(private Connection $db, private PasswordHasher $hasher = new PasswordHasher()) { parent::__construct(); }
    protected function configure(): void
    {
        // No --password option: command-line arguments leak via process lists and shell history.
        $this->addArgument('email', InputArgument::REQUIRED)->addOption('admin', null, InputOption::VALUE_NONE)
            ->setHelp('Reads the password from APP_USER_PASSWORD, or prompts for it (hidden) when interactive.');
    }
    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $email = strtolower(trim($input->getArgument('email')));
        $password = getenv('APP_USER_PASSWORD') ?: null;
        if ($password === null && $input->isInteractive()) {
            $question = (new Question('Password (12+ characters, no spaces): '))->setHidden(true)->setHiddenFallback(false);
            $password = $this->getHelper('question')->ask($input, $output, $question);
        }
        if (!filter_var($email, FILTER_VALIDATE_EMAIL) || !is_string($password) || ($error = PasswordHasher::policyError($password))) {
            $output->writeln('<error>Valid email and password required: '.($error ?? 'set APP_USER_PASSWORD or run interactively').'</error>'); return Command::FAILURE;
        }
        $this->db->insert('users', ['id' => Uuid::v7()->toRfc4122(), 'email' => $email, 'password_hash' => $this->hasher->hash($password),
            'roles' => json_encode($input->getOption('admin') ? ['ROLE_USER', 'ROLE_ADMIN'] : ['ROLE_USER']), 'locale' => 'en', 'disabled' => 0]);
        $output->writeln('User created'); return Command::SUCCESS;
    }
}
