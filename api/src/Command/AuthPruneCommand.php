<?php
namespace App\Command;

use App\Service\Auth;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;

#[AsCommand(name: 'app:auth:prune', description: 'Delete expired refresh tokens and ended login throttle windows')]
final class AuthPruneCommand extends Command
{
    public function __construct(private Auth $auth) { parent::__construct(); }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $deleted = $this->auth->prune();
        $output->writeln(sprintf('Pruned %d refresh tokens and %d throttle windows', $deleted['tokens'], $deleted['throttles']));
        return Command::SUCCESS;
    }
}
